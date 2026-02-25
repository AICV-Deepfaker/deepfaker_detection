"""
Token CRUD
"""

from uuid import UUID
from datetime import datetime

from sqlmodel import select, update, col
from sqlmodel.orm.session import Session

from ddp_backend.models import Token

from .base import CRUDBase

__all__ = [
    "CRUDToken",
]


class CRUDToken(CRUDBase):
    # 사용 : 로그인

    @classmethod
    def upsert_token(cls, db: Session, user_id: UUID, hashed_refresh_token: str, expires_at: datetime):
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
        cls.commit_or_flush(db)
        db.refresh(token)
        return token

    # 사용 : refresh 토큰 갱신 (access_token은 DB 접근 X), 로그아웃(revoked 조회)
    @classmethod
    def get_by_refresh(cls, db: Session, hashed_refresh_token: str):
        """refresh token으로 토큰 조회"""
        query = select(Token).where(Token.refresh_token == hashed_refresh_token)
        return db.scalars(query).one_or_none()

    # 사용 : 로그아웃
    @classmethod
    def set_revoked(cls, db: Session, hashed_refresh_token: str):
        """토큰 비활성화"""
        token = CRUDToken.get_by_refresh(db, hashed_refresh_token)
        if token is None:
            return False
        token.revoked = True
        cls.commit_or_flush(db)
        return True

    @classmethod
    def bulk_revoke_expired(cls, db: Session):
        expired = datetime.now()
        query = (
            update(Token)
            .where(col(Token.revoked) == False)
            .where(col(Token.expires_at) < expired)
            .values(revoked=True)
        )
        db.exec(query, execution_options={'synchronize_session': False})

        cls.commit_or_flush(db)