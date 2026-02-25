from typing import Literal

from pydantic import BaseModel, computed_field, field_serializer

from ddp_backend.core.s3 import to_public_url
from ddp_backend.models.report import DeepReportData, FastReportData, STTScript

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
    visual_report: str | None

    @computed_field
    @property
    def confidence_score(self) -> float:
        return self.probability if self.probability > 0.5 else 1 - self.probability

    @field_serializer('visual_report')
    def vis_report_s3_key_to_path(self, value: str | None, _info): # type: ignore
        if value is None:
            return None
        return to_public_url(value)


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
