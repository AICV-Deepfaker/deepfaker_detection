from enum import StrEnum

__all__ = [
    "ModelName",
    "Status",
    "Result",
    "AnalyzeMode",
    "LoginMethod",
    "Affiliation",
    "VideoStatus",
    "OriginPath",
    "STTRiskLevel",
]


class ModelName(StrEnum):
    R_PPG = "r_ppg"
    UNITE = "unite"
    WAVELET = "wavelet"
    STT = "stt"


class Status(StrEnum):
    SUCCESS = "success"
    ERROR = "error"


class Result(StrEnum):
    REAL = "REAL"
    FAKE = "FAKE"
    UNKNOWN = "UNKNOWN"


class AnalyzeMode(StrEnum):
    FAST = "fast"
    DEEP = "deep"


class LoginMethod(StrEnum):
    LOCAL = "local"
    GOOGLE = "google"


class Affiliation(StrEnum):
    IND = "개인"
    ORG = "기관"
    COM = "회사"


class VideoStatus(StrEnum):  # 필요하지 않을 경우 삭제
    QUEUED = "queued"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OriginPath(StrEnum):
    LINK = "link"
    UPLOAD = "upload"


class STTRiskLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"
