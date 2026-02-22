"""
Token CRUD
"""

from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ddp_backend.models import Token

__all__ = [
    "TokenCreate",
    "CRUDToken",
]


class TokenCreate(BaseModel):
    user_id: int
    refresh_token: str
    # device_uuid: str
    expires_at: datetime


class CRUDToken:
    # 사용 : 로그인

    @staticmethod
    def create(db: Session, token_info: TokenCreate):
        """토큰 저장"""
        db_token = Token(  # 객체
            user_id=token_info.user_id,
            refresh_token=token_info.refresh_token,
            # device_uuid=token_info.device_uuid, # 기기 수집 (이후 개발 예정)
            expires_at=token_info.expires_at,
        )

        db.add(db_token)
        db.commit()
        db.refresh(db_token)
        return db_token

    # 사용 : refresh 토큰 갱신 (access_token은 DB 접근 X), 로그아웃(revoked 조회)
    @staticmethod
    def get_by_refresh(db: Session, refresh_token: str):
        """refresh token으로 토큰 조회"""
        query = select(Token).where(Token.refresh_token == refresh_token)
        return db.scalars(query).one_or_none()

    # 사용 : 로그아웃
    @staticmethod
    def update_revoked(db: Session, refresh_token: str):
        """토큰 비활성화"""
        token = CRUDToken.get_by_refresh(db, refresh_token)
        if token is None:
            return False
        token.revoked = True
        db.commit()
        return True
