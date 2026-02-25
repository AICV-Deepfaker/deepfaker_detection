from typing import Literal

from pydantic import BaseModel, computed_field

from ddp_backend.models.report import DeepReportData, FastReportData

from .enums import AnalyzeMode, ModelName, Result, Status, STTRiskLevel

__all__ = [
    "VideoReport",
    "STTScript",
    "STTReport",
    "FastReportData",
    "DeepReportData",
    "FastReportResponse",
    "DeepReportResponse"
]


class BaseReport(BaseModel):
    status: Status
    model_name: ModelName


class VideoReport(BaseReport):
    result: Result
    probability: float
    visual_report: str

    @computed_field
    @property
    def confidence_score(self) -> float:
        return self.probability if self.probability > 0.5 else 1 - self.probability


class STTScript(BaseModel):
    keywords: list[str]
    risk_reason: str
    transcript: str
    search_results: list[dict[str, str]]


class STTReport(BaseReport, STTScript):
    risk_level: STTRiskLevel


class BaseReportResponse(BaseModel):
    status: Status
    error_msg: str | None = None
    # analysis_mode: AnalyzeMode
    result: Result


class FastReportResponse(BaseReportResponse):
    analysis_mode: Literal[AnalyzeMode.FAST] = AnalyzeMode.FAST
    r_ppg: VideoReport | None = None
    wavelet: VideoReport | None = None
    stt: STTReport | None = None


class DeepReportResponse(BaseReportResponse):
    analysis_mode: Literal[AnalyzeMode.DEEP] = AnalyzeMode.DEEP
    unite: VideoReport | None = None
