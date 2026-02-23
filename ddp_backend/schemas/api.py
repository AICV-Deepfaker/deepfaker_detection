from typing import Literal

from pydantic import BaseModel

from .enums import AnalyzeMode, Result, Status
from .report import STTReport, VideoReport

__all__ = [
    "BaseAPIOutput",
    "APIOutputFast",
    "APIOutputDeep",
    "WorkerPubSubAPI",
]


class BaseAPIOutput(BaseModel):
    status: Status
    error_msg: str | None = None
    # analysis_mode: AnalyzeMode
    result: Result


class APIOutputFast(BaseAPIOutput):
    analysis_mode: Literal[AnalyzeMode.FAST] = AnalyzeMode.FAST
    r_ppg: VideoReport | None = None
    wavelet: VideoReport | None = None
    stt: STTReport | None = None


class APIOutputDeep(BaseAPIOutput):
    analysis_mode: Literal[AnalyzeMode.DEEP] = AnalyzeMode.DEEP
    unite: VideoReport | None = None


class WorkerPubSubAPI(BaseModel):
    user_id: int
    result_id: int
