from pathlib import Path

from pydantic import BaseModel
from stt import SCAM_SEED_KEYWORDS, STTPipelineResult, run_pipeline, RiskLevel

from .base_detector import BaseDetector

class STTReport(BaseModel):
    keywords: list[dict[str, str|bool]]
    risk_level: RiskLevel
    risk_reason: str
    transcript: str
    search_results: list[dict[str, str]]

class STTDetector(BaseDetector[BaseModel, STTReport]):
    def __init__(self):
        super().__init__(BaseModel())

    def load_model(self):
        pass

    async def _analyze(self, vid_path: str | Path) -> STTPipelineResult:
        return await run_pipeline(str(vid_path))

    async def analyze(self, vid_path: str | Path) -> STTReport:
        result = await self._analyze(vid_path)
        detected_set = set(result.detected_keywords)
        # 시드 키워드 전체를 detected 여부와 함께 반환
        stt_keywords: list[dict[str, str|bool]] = [
            {"keyword": kw, "detected": kw in detected_set} for kw in SCAM_SEED_KEYWORDS
        ]
        # 시드에 없는 감지 키워드도 추가
        for kw in result.detected_keywords:
            if kw not in SCAM_SEED_KEYWORDS:
                stt_keywords.append({"keyword": kw, "detected": True})
        return STTReport(
            keywords=stt_keywords,
            risk_level=result.risk_level,
            risk_reason=result.risk_reason,
            transcript=result.transcript,
            search_results=result.search_results,
        )
