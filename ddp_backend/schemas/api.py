from pydantic import BaseModel

from .enums import AnalyzeMode, Status, Result
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
    analysis_mode: AnalyzeMode
    result: Result


class APIOutputFast(BaseAPIOutput):
    r_ppg: VideoReport | None = None
    wavelet: VideoReport | None = None
    stt: STTReport | None = None


class APIOutputDeep(BaseAPIOutput):
    unite: VideoReport | None = None

class WorkerPubSubAPI(BaseModel):
    user_id: int
    result_id: int
