# 테이블이 4개 정도이므로 하나의 파일로 테이블 구성
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ddp_backend.core.database import Base
from pydantic import BaseModel
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Dialect,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator

from ddp_backend.schemas.enums import (
    LoginMethod,
    Affiliation,
    VideoStatus,
    OriginPath,
    STTRiskLevel,
)
from ddp_backend.schemas.enums import Result as ResultEnum
from ddp_backend.schemas.report import STTScript


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



# 1. Users table
class User(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, index=True, autoincrement=True, init=False
    )  # 효율성을 위해 user만 index=True
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    login_method: Mapped[LoginMethod | None] = mapped_column(
        Enum(LoginMethod), nullable=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255))  # 자체 로그인 시에만 사용
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    nickname: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    birth: Mapped[date] = mapped_column(Date, nullable=False)
    profile_image: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )  # 필요 없을 경우 삭제
    affiliation: Mapped[Affiliation | None] = mapped_column(
        Enum(Affiliation), nullable=True
    )
    activation_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )
    # Relationships
    tokens: Mapped[Token] = relationship(
        "Token", back_populates="user", cascade="all, delete-orphan", init=False
    )
    videos: Mapped[list[Video]] = relationship(
        "Video", back_populates="user", cascade="all, delete-orphan", init=False
    )
    results: Mapped[list[Result]] = relationship(
        "Result", back_populates="user", cascade="all, delete-orphan", init=False
    )
    fast_reports: Mapped[list[FastReport]] = relationship(
        "FastReport", back_populates="user", cascade="all, delete-orphan", init=False
    )
    deep_reports: Mapped[list[DeepReport]] = relationship(
        "DeepReport", back_populates="user", cascade="all, delete-orphan", init=False
    )
    alerts: Mapped[list[Alert]] = relationship(
        "Alert", back_populates="user", cascade="all, delete-orphan", init=False
    )


# 2. Tokens table
class Token(Base):
    __tablename__ = "tokens"
    token_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, init=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE")
    )  # ondelete = 유저 삭제 시 함께 삭제
    refresh_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # device_uuid:Mapped[str] = mapped_column(String(255)) # 토큰 보안과 연관 (필요 없을 경우 삭제) # 추후 개발
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # 토큰 만료
    created_at: Mapped[datetime] = mapped_column( # refresh 토큰 생성 시간
        DateTime(timezone=True), server_default=func.now(), init=False
    )
    # With default
    revoked: Mapped[bool] = mapped_column( # 로그아웃 되었거나 보안상 차단된 토큰 -> True시 반드시 재로그인
        Boolean, default=False
    )  
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="tokens", init=False)



# 3. Videos table
class Video(Base):
    __tablename__ = "videos"
    video_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, init=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE")
    )
    origin_path: Mapped[OriginPath] = mapped_column(Enum(OriginPath), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus), server_default=VideoStatus.pending.value, init=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="videos", init=False)
    sources: Mapped[Source] = relationship(
        "Source", back_populates="video", cascade="all, delete-orphan", init=False
    )
    results: Mapped[list[Result]] = relationship(
        "Result", back_populates="video", cascade="all, delete-orphan", init=False
    )


# 4. Sources table (12시간이 지난 video 테이블, s3는 삭제)
class Source(Base):  # S3 관리용 (일정 시간 후 삭제 대상)
    __tablename__ = "sources"
    source_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, init=False,
    )
    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("videos.video_id", ondelete="CASCADE")
    )
    s3_path: Mapped[str] = mapped_column(String(500), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False
    )  # 12시간 후 만료 등
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )
    # Relationships
    video: Mapped[Video] = relationship("Video", back_populates="sources", init=False)


# 5. Results table
class Result(Base):
    __tablename__ = "results"
    result_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, init=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE")
    )
    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("videos.video_id", ondelete="CASCADE")
    )
    is_fast: Mapped[bool] = mapped_column(Boolean)
    is_fake: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="results", init=False)
    video: Mapped[Video] = relationship("Video", back_populates="results", init=False)
    fast_report: Mapped[FastReport] = relationship(
        "FastReport",
        back_populates="result",
        uselist=False,
        cascade="all, delete-orphan",
        init=False,
    )
    deep_report: Mapped[DeepReport] = relationship(
        "DeepReport",
        back_populates="result",
        uselist=False,
        cascade="all, delete-orphan",
        init=False,
    )
    alerts: Mapped[list[Alert]] = relationship("Alert", back_populates="result", init=False)


# 6. FastReports table
class FastReport(Base):
    __tablename__ = "fast_reports"
    fast_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, init=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE")
    )
    result_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("results.result_id", ondelete="CASCADE")
    )
    freq_result: Mapped[ResultEnum] = mapped_column(Enum(ResultEnum), nullable=False)
    freq_conf: Mapped[float] = mapped_column(Float, nullable=False)
    freq_image: Mapped[str] = mapped_column(String(255), nullable=False)
    rppg_result: Mapped[ResultEnum] = mapped_column(Enum(ResultEnum), nullable=False)
    rppg_conf: Mapped[float] = mapped_column(Float, nullable=False)
    rppg_image: Mapped[str] = mapped_column(String(255), nullable=False)
    stt_risk_level: Mapped[STTRiskLevel] = mapped_column(
        Enum(STTRiskLevel), nullable=False
    )
    stt_script: Mapped[STTScript] = mapped_column(
        PydanticJSONType(STTScript), nullable=False
    )
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="fast_reports", init=False)
    result: Mapped[Result] = relationship(
        "Result", back_populates="fast_report", init=False
    )


# 7. DeepReports table
class DeepReport(Base):
    __tablename__ = "deep_reports"
    deep_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, init=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE")
    )
    result_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("results.result_id", ondelete="CASCADE")
    )
    unite_result: Mapped[ResultEnum] = mapped_column(Enum(ResultEnum), nullable=False)
    unite_conf: Mapped[float] = mapped_column(Float, nullable=False)
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="deep_reports", init=False)
    result: Mapped[Result] = relationship(
        "Result", back_populates="deep_report", init=False
    )


# 8. Alerts table
class Alert(Base):  # 신고하기
    __tablename__ = "alerts"
    alert_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, init=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE")
    )
    result_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("results.result_id", ondelete="SET NULL"), nullable=True
    )
    alerted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="alerts", init=False)
    result: Mapped[Result] = relationship(
        "Result", back_populates="alerts", passive_deletes=True, init=False
    )
