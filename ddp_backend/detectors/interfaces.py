from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from ddp_backend.schemas.enums import ModelName
from ddp_backend.schemas.report import STTReport, VideoReport


class VisualDetector(ABC):
    model_name: ClassVar[ModelName]

    @abstractmethod
    def load_model(self):
        pass

    @abstractmethod
    def analyze(self, vid_path: str | Path) -> VideoReport:
        pass

class AudioAnalyzer(ABC):
    model_name: ClassVar[ModelName]

    @abstractmethod
    def analyze(self, vid_path: str | Path) -> STTReport:
        pass