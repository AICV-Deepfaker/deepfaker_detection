from pydantic import BaseModel

from .enums import AnalyzeMode, Status
from .report import STTReport, VideoReport

__all__ = [
    "BaseAPIOutput",
    "APIOutputFast",
    "APIOutputDeep",
]


class BaseAPIOutput(BaseModel):
    status: Status
    error_msg: str | None = None
    analysis_mode: AnalyzeMode


class APIOutputFast(BaseAPIOutput):
    r_ppg: VideoReport | None = None
    wavelet: VideoReport | None = None
    stt: STTReport | None = None


class APIOutputDeep(BaseAPIOutput):
    unite: VideoReport | None = None
