from enum import StrEnum


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


class AnalyzeMode(StrEnum):
    FAST = "fast"
    DEEP = "deep"

class LoginMethod(StrEnum):
    local = "local"
    google = "google"


class Affiliation(StrEnum):
    ind = "개인"
    org = "기관"
    com = "회사"


class VideoStatus(StrEnum):  # 필요하지 않을 경우 삭제
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class OriginPath(StrEnum):
    link = "link"
    upload = "upload"


class STTRiskLevel(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"
    none = "none"