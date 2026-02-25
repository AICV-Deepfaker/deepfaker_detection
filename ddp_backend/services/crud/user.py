"""
User CRUD
"""

from uuid import UUID
from datetime import date

from pydantic import BaseModel
from sqlmodel import select, Session
from sqlalchemy.exc import NoResultFound

from ddp_backend.models import User
from ddp_backend.schemas.user import UserCreateCRUD
from ddp_backend.schemas.enums import Affiliation
from ddp_backend.core.s3 import delete_keys_from_s3  # 배치 삭제 함수

from .base import CRUDBase

__all__ = [
    "CRUDUser",
]



class UserUpdate(BaseModel):
    hashed_password: str | None = None
    profile_image: str | None = None
    affiliation: Affiliation | None = None


class CRUDUser(CRUDBase):
    # 사용 : 회원가입
    @classmethod
    def create(cls, db: Session, user_create: UserCreateCRUD):
        """유저 생성"""
        db_user = User.model_validate(user_create)
        db.add(db_user)  # db_user에 추가
        cls.commit_or_flush(db)
        db.refresh(db_user)  # DB에서 다시 읽기
        return db_user

    # 사용 : 회원가입, 로그인, 회원정보수정, 포인트 조회
    @classmethod
    def get_by_email(cls, db: Session, email: str):
        """이메일 조회"""
        return db.exec(select(User).where(User.email == email)).one_or_none()  # One user per one email

    # 사용 : 회원가입
    @classmethod
    def get_by_nickname(cls, db: Session, nickname: str):
        """닉네임 중복 체크"""
        return db.exec(select(User).where(User.nickname == nickname)).one_or_none()

    # 사용 : user_id로 조회
    @classmethod
    def get_by_id(cls, db: Session, user_id: UUID):  # 공통
        """user_id로 유저 조회"""
        return db.get(User, user_id)

    # 사용 : 아이디 찾기
    @classmethod
    def get_by_name_birth(cls, db: Session, name: str, birth: date):
        """이름, 생년월일 조회"""
        return db.exec(select(User).where(User.name == name, User.birth == birth)).first()

    # 사용 : 비밀번호 찾기
    @classmethod
    def get_by_name_birth_email(cls, db: Session, name: str, birth: date, email: str):
        """이름, 생년월일, 이메일 조회"""
        return db.exec(select(User).where(
            User.name == name, User.birth == birth, User.email == email
        )).one_or_none()

    # 사용 : 회원정보수정
    @classmethod
    def update(cls, db: Session, user_id: UUID, update_info: UserUpdate):
        """유저 정보 변경"""
        user = CRUDUser.get_by_id(db, user_id)
        if user is None:
            return None

        if update_info.hashed_password is not None:  # pw
            user.hashed_password = update_info.hashed_password
        if update_info.profile_image is not None:  # 프로필
            user.profile_image = update_info.profile_image
        if update_info.affiliation is not None:  # 소속
            user.affiliation = update_info.affiliation

        cls.commit_or_flush(db)
        db.refresh(user)
        return user
    
    # 사용 : 이미지 삭제
    @classmethod
    def delete_profile_image(cls, db: Session, user_id: UUID):
        user = CRUDUser.get_by_id(db, user_id)
        if user is None:
            return None
        user.profile_image = None
        cls.commit_or_flush(db)
        db.refresh(user)
        return user

    # 사용 : 포인트 업데이트
    @classmethod
    def update_active_points(cls, db: Session, user_id: UUID, points: int):
        """포인트 업데이트"""
        user = CRUDUser.get_by_id(db, user_id)
        if user is None:
            raise NoResultFound
        user.activation_points += points  # 1000점
        cls.commit_or_flush(db)
        db.refresh(user)
        return user.activation_points

    # 사용 : 회원탈퇴
    @classmethod
    def delete(cls, db: Session, user_id: UUID):
        """유저 삭제"""
        user = CRUDUser.get_by_id(db, user_id)
        if user is None:
            return False
        db.delete(user)
        cls.commit_or_flush(db)
        return True
        # 사용 : 회원탈퇴 (S3 파일까지 정리)
    @classmethod
    def delete_with_s3_cleanup(cls, db: Session, user_id: UUID) -> bool:
        """
        유저 탈퇴 시 S3에 저장된 프로필/영상 파일도 함께 삭제.
        - DB에는 user.profile_image (URL 또는 key)
        - videos/source에는 source.s3_path (URL 또는 key)
        """
        user = CRUDUser.get_by_id(db, user_id)
        if user is None:
            return False

        # 1) 삭제 대상 모으기 (URL이든 key든 상관없음)
        targets: list[str] = []

        if getattr(user, "profile_image", None):
            targets.append(user.profile_image)

        # user.videos 관계가 있는 경우에만 순회
        videos = getattr(user, "videos", None)
        if videos:
            for video in videos:
                src = getattr(video, "source", None)
                if src and getattr(src, "s3_path", None):
                    targets.append(src.s3_path)

                # 만약 추가 파일 경로가 있다면 여기서 함께 append 가능
                # if getattr(video, "processed_s3_path", None): targets.append(video.processed_s3_path)
                # if getattr(video, "thumb_s3_path", None): targets.append(video.thumb_s3_path)

        # 2) S3 배치 삭제 (실패해도 탈퇴는 진행: 현재 코드 스타일 유지)
        try:
            delete_keys_from_s3(targets)
        except Exception:
            pass

        # 3) DB 삭제 (기존 delete 로직 재사용)
        db.delete(user)
        cls.commit_or_flush(db)
        return True