"""
Report CRUD
"""

from uuid import UUID
from sqlmodel import select
from sqlmodel.orm.session import Session

from ddp_backend.models import DeepReport, FastReport

__all__ = [
    "CRUDFastReport",
    "CRUDDeepReport",
]


class CRUDFastReport:
    # 사용 : FastReport 저장
    @staticmethod
    def create(db: Session, db_report: FastReport):
        """Fast 분석 리포트 생성"""
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        return db_report

    # 사용 : FastReport 상세 결과 조회
    @staticmethod
    def get_by_result(db: Session, result_id: UUID):
        """result_id로 Fast 리포트 조회"""
        query = select(FastReport).where(FastReport.result_id == result_id)
        return db.scalars(query).one_or_none()


class CRUDDeepReport:
    # 사용 : DeepReport 저장
    @staticmethod
    def create(db: Session, db_report: DeepReport):
        """Deep 분석 리포트 생성"""
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        return db_report

    # 사용 : DeepReport 상세 결과 조회
    @staticmethod
    def get_by_result(db: Session, result_id: UUID):
        """result_id로 Deep 리포트 조회"""
        query = select(DeepReport).where(DeepReport.result_id == result_id)
        return db.scalars(query).one_or_none()
