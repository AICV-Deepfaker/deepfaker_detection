from pathlib import Path

from .base_detector import BaseDetector
from stt import run_pipeline, SCAM_SEED_KEYWORDS, STTPipelineResult


class STTDetector(BaseDetector[STTPipelineResult]):
    def load_model(self):
        pass

    async def _analyze(self, video_path: str | Path) -> STTPipelineResult:
        return await run_pipeline(video_path)

    async def analyze(self, video_path: str | Path) -> dict:
        result = await self._analyze()
        detected_set = set(result.detected_keywords)
        # 시드 키워드 전체를 detected 여부와 함께 반환
        stt_keywords = [
            {"keyword": kw, "detected": kw in detected_set}
            for kw in SCAM_SEED_KEYWORDS
        ]
        # 시드에 없는 감지 키워드도 추가
        for kw in result.detected_keywords:
            if kw not in SCAM_SEED_KEYWORDS:
                stt_keywords.append({"keyword": kw, "detected": True})
        return {
            "keywords": stt_keywords,
            "risk_level": result.risk_level,
            "risk_reason": result.risk_reason,
            "transcript": result.transcript,
            "search_results": result.search_results,
        }