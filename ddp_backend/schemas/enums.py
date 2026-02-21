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