from typing import Annotated, Literal

from pydantic import BaseModel, Field, computed_field, field_serializer, model_serializer

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

class ProbabilityContent(BaseModel):
    probability: float

    @computed_field
    @property
    def result(self) -> Result:
        if self.probability > 0.5:
            return Result.REAL
        if self.probability < 0.5:
            return Result.FAKE
        return Result.UNKNOWN

    @property
    def confidence_score(self) -> float:
        return self.probability if self.probability > 0.5 else 1 - self.probability

class VisualContent(BaseModel):
    image: Annotated[bytes | None, Field(exclude=True)] = None
    visual_report: str | None = None

    @field_serializer('visual_report')
    def vis_report_s3_key_to_path(self, value: str | None, _info): # type: ignore
        if value is None:
            return None
        return to_public_url(value)

class ProbVisualContent(ProbabilityContent, VisualContent): ...

class VideoReport[Content: BaseModel](BaseReport):
    content: Content | None = None

    @model_serializer
    def content_flattener(self):
        base_dict = {
            'status': self.status,
            'model_name': self.model_name,
        }
        if self.content is None:
            return base_dict
        content_dict = self.content.model_dump()
        return {**base_dict, **content_dict}



class STTReport(BaseReport, STTScript):
    risk_level: STTRiskLevel


class BaseReportResponse(BaseModel):
    status: Status
    error_msg: str | None = None
    # analysis_mode: AnalyzeMode
    result: Result


class FastReportResponse(BaseReportResponse):
    analysis_mode: Literal[AnalyzeMode.FAST] = AnalyzeMode.FAST
    r_ppg: VideoReport[VisualContent] | None = None
    wavelet: VideoReport[ProbVisualContent] | None = None
    stt: STTReport | None = None


class DeepReportResponse(BaseReportResponse):
    analysis_mode: Literal[AnalyzeMode.DEEP] = AnalyzeMode.DEEP
    unite: VideoReport[ProbabilityContent] | None = None
