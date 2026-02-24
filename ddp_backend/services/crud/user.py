"""
User CRUD
"""

from uuid import UUID
from datetime import date

from pydantic import BaseModel
from sqlmodel import select
from sqlalchemy.exc import NoResultFound
from sqlmodel.orm.session import Session

from ddp_backend.models import User
from ddp_backend.schemas.user import UserCreateCRUD
from ddp_backend.schemas.enums import Affiliation

__all__ = [
    "CRUDUser",
]



class UserUpdate(BaseModel):
    hashed_password: str | None = None
    profile_image: str | None = None
    affiliation: Affiliation | None = None


class CRUDUser:
    # 사용 : 회원가입
    @staticmethod
    def create(db: Session, user_create: UserCreateCRUD):
        """유저 생성"""
        db_user = User.model_validate(user_create)
        db.add(db_user)  # db_user에 추가
        db.commit()  # DB에 저장
        db.refresh(db_user)  # DB에서 다시 읽기
        return db_user

    # 사용 : 회원가입, 로그인, 회원정보수정, 포인트 조회
    @staticmethod
    def get_by_email(db: Session, email: str):
        """이메일 조회"""
        query = select(User).where(User.email == email)
        return db.scalars(query).one_or_none()  # One user per one email

    # 사용 : 회원가입
    @staticmethod
    def get_by_nickname(db: Session, nickname: str):
        """닉네임 중복 체크"""
        query = select(User).where(User.nickname == nickname)
        return db.scalars(
            query
        ).one_or_none()

    # 사용 : user_id로 조회
    @staticmethod
    def get_by_id(db: Session, user_id: UUID):  # 공통
        """user_id로 유저 조회"""
        return db.get(User, user_id)

    # 사용 : 아이디 찾기
    @staticmethod
    def get_by_name_birth(db: Session, name: str, birth: date):
        """이름, 생년월일 조회"""
        query = select(User).where(User.name == name, User.birth == birth)
        return db.scalars(query).first()

    # 사용 : 비밀번호 찾기
    @staticmethod
    def get_by_name_birth_email(db: Session, name: str, birth: date, email: str):
        """이름, 생년월일, 이메일 조회"""
        query = select(User).where(
            User.name == name, User.birth == birth, User.email == email
        )
        return db.scalars(query).one_or_none()

    # 사용 : 회원정보수정
    @staticmethod
    def update(db: Session, user_id: UUID, update_info: UserUpdate):
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

        db.commit()
        db.refresh(user)
        return user
    
    # 사용 : 이미지 삭제
    @staticmethod
    def delete_profile_image(db: Session, user_id: UUID):
        user = CRUDUser.get_by_id(db, user_id)
        if user is None:
            return None
        user.profile_image = None
        db.commit()
        db.refresh(user)
        return user

    # 사용 : 포인트 업데이트
    @staticmethod
    def update_active_points(db: Session, user_id: UUID, points: int):
        """포인트 업데이트"""
        user = CRUDUser.get_by_id(db, user_id)
        if user is None:
            raise NoResultFound
        user.activation_points += points  # 1000점
        db.commit()
        db.refresh(user)
        return user.activation_points

    # 사용 : 회원탈퇴
    @staticmethod
    def delete(db: Session, user_id: UUID):
        """유저 삭제"""
        user = CRUDUser.get_by_id(db, user_id)
        if user is None:
            return False
        db.delete(user)
        db.commit()
        return True
