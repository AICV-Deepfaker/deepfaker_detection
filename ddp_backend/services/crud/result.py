"""
Result CRUD
"""

from uuid import UUID

from sqlmodel import select
from sqlmodel.orm.session import Session

from ddp_backend.models import Result
from ddp_backend.schemas.enums import Result as ResultEnum

from .base import CRUDBase

__all__ = [
    "CRUDResult",
]


class CRUDResult(CRUDBase):
    # 사용 : AI 분석 결과 저장
    @classmethod
    def create(cls, db: Session, db_result: Result):
        """분석 결과 생성"""
        db.add(db_result)
        cls.commit_or_flush(db)
        db.refresh(db_result)
        return db_result

    # 사용 : 히스토리, 상세결과 조회, 공유 페이지
    @classmethod
    def get_by_id(cls, db: Session, result_id: UUID):
        """result_id로 결과 조회"""
        return db.get(Result, result_id)

    @classmethod
    def get_by_video_id(cls, db: Session, video_id: UUID):
        query = select(Result).where(Result.video_id == video_id)
        return db.scalars(query).one_or_none()

    @classmethod
    def update(
        cls,
        db: Session,
        result_id: UUID,
        is_fast: bool | None = None,
        total_result: ResultEnum | None = None,
    ):
        res = CRUDResult.get_by_id(db, result_id)
        if res is None:
            return None
        if is_fast is not None:
            res.is_fast = is_fast
        if total_result is not None:
            res.total_result = total_result
        cls.commit_or_flush(db)
        db.refresh(res)
        return res

    # 사용 : 히스토리 삭제
    @classmethod
    def delete(cls, db: Session, result_id: UUID):
        """결과 삭제 (FastReport, DeepReport 함께 삭제)"""
        result = CRUDResult.get_by_id(db, result_id)
        if result is None:
            return False
        db.delete(result)
        cls.commit_or_flush(db)
        return True
