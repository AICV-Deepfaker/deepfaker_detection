from pydantic import BaseModel, computed_field

from .enums import ModelName, Result, Status, STTRiskLevel

__all__ = ["VideoReport", "STTScript", "STTReport"]


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
