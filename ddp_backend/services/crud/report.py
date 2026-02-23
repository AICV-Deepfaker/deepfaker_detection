"""
Report CRUD
"""

from uuid import UUID
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ddp_backend.models import DeepReport, FastReport
from ddp_backend.schemas.enums import STTRiskLevel, Result
from ddp_backend.schemas.report import STTScript

__all__ = [
    "FastReportCreate",
    "DeepReportCreate",
    "CRUDFastReport",
    "CRUDDeepReport",
]


class FastReportCreate(BaseModel):
    user_id: UUID
    result_id: UUID
    freq_result: Result
    freq_conf: float
    freq_image: str
    rppg_result: Result
    rppg_conf: float
    rppg_image: str
    stt_risk_level: STTRiskLevel
    stt_script: STTScript


class DeepReportCreate(BaseModel):
    user_id: UUID
    result_id: UUID
    unite_result: Result
    unite_conf: float


class CRUDFastReport:
    # 사용 : FastReport 저장
    @staticmethod
    def create(db: Session, report_info: FastReportCreate):
        """Fast 분석 리포트 생성"""
        db_report = FastReport(
            user_id=report_info.user_id,
            result_id=report_info.result_id,
            freq_result=report_info.freq_result,
            freq_conf=report_info.freq_conf,
            freq_image=report_info.freq_image,
            rppg_result=report_info.rppg_result,
            rppg_conf=report_info.rppg_conf,
            rppg_image=report_info.rppg_image,
            stt_risk_level=report_info.stt_risk_level,
            stt_script=report_info.stt_script,
        )
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
    def create(db: Session, report_info: DeepReportCreate):
        """Deep 분석 리포트 생성"""
        db_report = DeepReport(
            user_id=report_info.user_id,
            result_id=report_info.result_id,
            unite_result=report_info.unite_result,
            unite_conf=report_info.unite_conf,
        )
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
