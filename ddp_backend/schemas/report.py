from pydantic import BaseModel, computed_field
from stt import RiskLevel

from .enums import ModelName, Result, Status


class BaseReport(BaseModel):
    status: Status
    model_name: ModelName


class VideoReport(BaseReport):
    result: Result
    probability: float
    visual_report: str

    @computed_field
    @property
    def confidence_score(self) -> str:
        confidence = (
            self.probability if self.probability > 0.5 else 1 - self.probability
        )
        return f"{round(confidence * 100, 2)}%"


class STTScript(BaseModel):
    risk_reason: str
    transcript: str
    search_results: list[dict[str, str]]


class STTReport(BaseReport, STTScript):
    keywords: list[dict[str, str | bool]]
    risk_level: RiskLevel
