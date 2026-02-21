from pathlib import Path

from .base_detector import BaseVideoDetector, BaseVideoConfig, VideoInferenceResult


class RPPGDetector(BaseVideoDetector[BaseVideoConfig]):
    def load_model(self):
        pass

    async def _analyze(self, vid_path: str | Path) -> VideoInferenceResult:
        return VideoInferenceResult(prob=0, base64_report="dummy")
