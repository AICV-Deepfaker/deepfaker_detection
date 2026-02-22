from pathlib import Path
from typing import final, override
import sys
import os

# STT 폴더가 있는 절대 경로를 파이썬에게 알려줍니다.
sys.path.append("/content/deepfaker_detection/STT")
sys.path.append("/content/deepfaker_detection")

from STT.src.stt.pipeline import SCAM_SEED_KEYWORDS, run_pipeline

from schemas.enums import ModelName, Status, STTRiskLevel
from schemas.report import STTReport
from detectors import AudioAnalyzer


@final
class STTDetector(AudioAnalyzer):
    model_name = ModelName.STT

    @override
    def analyze(self, vid_path: str | Path) -> STTReport:
        result = run_pipeline(str(vid_path))
        detected_set = set(result.detected_keywords)
        # 시드 키워드 전체를 detected 여부와 함께 반환
        stt_keywords: list[dict[str, str | bool]] = [
            {"keyword": kw, "detected": kw in detected_set} for kw in SCAM_SEED_KEYWORDS
        ]
        # 시드에 없는 감지 키워드도 추가
        for kw in result.detected_keywords:
            if kw not in SCAM_SEED_KEYWORDS:
                stt_keywords.append({"keyword": kw, "detected": True})
        return STTReport(
            status=Status.SUCCESS,
            model_name=self.model_name,
            keywords=result.detected_keywords,
            risk_level=STTRiskLevel(result.risk_level),
            risk_reason=result.risk_reason,
            transcript=result.transcript,
            search_results=result.search_results,
        )
