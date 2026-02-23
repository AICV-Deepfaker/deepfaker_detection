"""
Result CRUD
"""

from uuid import UUID
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ddp_backend.models import Result
from ddp_backend.schemas.enums import Result as ResultEnum

__all__ = [
    "ResultCreate",
    "CRUDResult",
]


class ResultCreate(BaseModel):
    user_id: UUID
    video_id: UUID
    total_result: ResultEnum
    is_fast: bool


class CRUDResult:
    # 사용 : AI 분석 결과 저장
    @staticmethod
    def create(db: Session, result_info: ResultCreate):
        """분석 결과 생성"""
        db_result = Result(
            user_id=result_info.user_id,
            video_id=result_info.video_id,
            is_fast=result_info.is_fast,
            total_result=result_info.total_result,
        )
        db.add(db_result)
        db.commit()
        db.refresh(db_result)
        return db_result

    # 사용 : 히스토리, 상세결과 조회, 공유 페이지
    @staticmethod
    def get_by_id(db: Session, result_id: UUID):
        """result_id로 결과 조회"""
        return db.get(Result, result_id)

    # 참조 : 링크를 상세결과에만 포함할 경우
    #       아래의 쿼리 대신 result.video.source_url 사용 (in service.py)

    # 사용 : 히스토리 목록에 링크 첨부 (필요시)
    # def get_result_with_video(db: Session, result_id: int):
    #     """ result_id로 결과 + 비디오(링크 호출용) 조회 """
    #     return db.query(Result)\
    #              .options(joinedload(Result.video))\
    #              .filter(Result.result_id == result_id)\
    #              .first()

    # 사용 : 히스토리 삭제
    @staticmethod
    def delete(db: Session, result_id: UUID):
        """결과 삭제 (FastReport, DeepReport 함께 삭제)"""
        result = CRUDResult.get_by_id(db, result_id)
        if result is None:
            return False
        db.delete(result)
        db.commit()
        return True
