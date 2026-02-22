from datetime import date, datetime

from pydantic import BaseModel

from .enums import Affiliation, OriginPath, STTRiskLevel
from .report import STTScript


class UserCreate(BaseModel):
    email: str
    hashed_password: str
    name: str
    nickname: str
    birth: date
    profile_image: str | None = None
    affiliation: Affiliation | None = None


class UserUpdate(BaseModel):
    hashed_password: str | None = None
    profile_image: str | None = None
    affiliation: Affiliation | None = None


class TokenCreate(BaseModel):
    user_id: int
    refresh_token: str
    # device_uuid: str
    expires_at: datetime


class VideoCreate(BaseModel):
    user_id: int
    origin_path: OriginPath
    source_url: str | None = None


class SourceCreate(BaseModel):
    video_id: int
    s3_path: str
    expires_at: datetime


class ResultCreate(BaseModel):
    user_id: int
    video_id: int
    is_fake: bool
    is_fast: bool


class FastReportCreate(BaseModel):
    user_id: int
    result_id: int
    freq_result: str
    freq_conf: float
    freq_image: str
    rppg_result: str
    rppg_conf: float
    rppg_image: str
    stt_keyword: str
    stt_risk_level: STTRiskLevel
    stt_script: STTScript


class DeepReportCreate(BaseModel):
    user_id: int
    result_id: int
    unite_result: str
    unite_conf: float


class AlertCreate(BaseModel):
    user_id: int
    result_id: int
