from typing import Literal

from pydantic import BaseModel
from stt import RiskLevel


class BaseReport(BaseModel):
    status: Literal["success"]
    model_name: str


class VideoReport(BaseReport):
    result: Literal["REAL", "FAKE"]
    average_fake_prob: float
    confidence_score: str
    visual_report: str


class STTReport(BaseReport):
    keywords: list[dict[str, str | bool]]
    risk_level: RiskLevel
    risk_reason: str
    transcript: str
    search_results: list[dict[str, str]]


class APIOutput(BaseModel):
    status: Literal["success", "error"]
    error_msg: str | None = None
    result: Literal["REAL", "FAKE"]
    average_fake_prob: float
    confidence_score: str
    analysis_mode: str
    reports: dict[str, BaseReport | VideoReport | STTReport]
