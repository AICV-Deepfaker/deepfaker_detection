from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel
from sqlalchemy import Dialect
from sqlalchemy.types import JSON, BigInteger, TypeDecorator
from sqlmodel import Field, Relationship

from ddp_backend.core.database import Base
from ddp_backend.schemas.enums import Result as ResultEnum
from ddp_backend.schemas.enums import STTRiskLevel
from ddp_backend.schemas.report import STTScript

from .models import MAX_S3_LEN

if TYPE_CHECKING:
    from .models import Result
    from .user import User


class PydanticJSONType[T: BaseModel](TypeDecorator[T]):
    impl = JSON
    cache_ok = True

    def __init__(self, pydantic_model: type[T]):
        super().__init__()
        self.pydantic_model = pydantic_model

    def process_bind_param(self, value: T | None, dialect: Dialect) -> Any:
        # Python 객체 -> DB 저장 (JSON 변환)
        if value is None:
            return None
        # Pydantic v2: model_dump_json() 또는 model_dump()
        return value.model_dump(mode="json")

    def process_result_value(self, value: Any, dialect: Dialect) -> T | None:
        # DB 값 -> Python 객체 (Pydantic 모델 변환)
        if value is None:
            return None
        # Pydantic v2: model_validate()
        return self.pydantic_model.model_validate(value)


class ReportBase(Base):
    user_id: uuid.UUID = Field(foreign_key="users.user_id", ondelete="CASCADE")
    result_id: uuid.UUID = Field(foreign_key="results.result_id", ondelete="CASCADE")

class FastReportData(Base):
    freq_result: ResultEnum
    freq_conf: float
    freq_image: str = Field(max_length=MAX_S3_LEN)
    rppg_result: ResultEnum
    rppg_conf: float
    rppg_image: str = Field(max_length=MAX_S3_LEN)
    stt_risk_level: STTRiskLevel
    stt_script: STTScript = Field(
        sa_type=PydanticJSONType(STTScript), # type: ignore
    )

class DeepReportData(Base):
    unite_result: ResultEnum
    unite_conf: float


class FastReport(ReportBase, FastReportData, table=True):
    __tablename__: str = "fast_reports"  # type: ignore
    fast_id: int | None = Field(default=None, primary_key=True, sa_type=BigInteger)

    user: User = Relationship(back_populates="fast_reports")
    result: Result = Relationship(back_populates="fast_report")


class DeepReport(ReportBase, DeepReportData, table=True):
    __tablename__: str = "deep_reports"  # type: ignore
    deep_id: int | None = Field(default=None, primary_key=True, sa_type=BigInteger)

    user: User = Relationship(back_populates="deep_reports")
    result: Result = Relationship(back_populates="deep_report")