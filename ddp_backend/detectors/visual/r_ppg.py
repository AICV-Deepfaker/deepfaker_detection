from pathlib import Path
from typing import final, override

from schemas.enums import ModelName

from .base import BaseVideoConfig, BaseVideoDetector, VideoInferenceResult


@final
class RPPGDetector(BaseVideoDetector[BaseVideoConfig]):
    model_name = ModelName.R_PPG

    @override
    def load_model(self):
        pass

    @override
    def _analyze(self, vid_path: str | Path) -> VideoInferenceResult:
        return VideoInferenceResult(prob=0, base64_report="dummy")
