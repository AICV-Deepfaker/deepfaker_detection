"""
Token CRUD
"""

from uuid import UUID
from datetime import datetime

from sqlmodel import select
from sqlmodel.orm.session import Session

from ddp_backend.models import Token

__all__ = [
    "CRUDToken",
]


class CRUDToken:
    # 사용 : 로그인

    @staticmethod
    def upsert_token(db: Session, user_id: UUID, hashed_refresh_token: str, expires_at: datetime):
        """토큰 업데이트 + 생성"""
        token = db.scalars(select(Token).where(Token.user_id == user_id)).one_or_none()
        if token:
            token.refresh_token = hashed_refresh_token
            token.expires_at = expires_at
            token.revoked = False
        else:
            token = Token(
                user_id=user_id,
                refresh_token=hashed_refresh_token,
                # device_uuid=token_info.device_uuid, # 기기 수집 (이후 개발 예정)
                expires_at=expires_at
            )
            db.add(token)
        db.commit()
        db.refresh(token)
        return token

    # 사용 : refresh 토큰 갱신 (access_token은 DB 접근 X), 로그아웃(revoked 조회)
    @staticmethod
    def get_by_refresh(db: Session, hashed_refresh_token: str):
        """refresh token으로 토큰 조회"""
        query = select(Token).where(Token.refresh_token == hashed_refresh_token)
        return db.scalars(query).one_or_none()

    # 사용 : 로그아웃
    @staticmethod
    def set_revoked(db: Session, hashed_refresh_token: str):
        """토큰 비활성화"""
        token = CRUDToken.get_by_refresh(db, hashed_refresh_token)
        if token is None:
            return False
        token.revoked = True
        db.commit()
        return True
