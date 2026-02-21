from abc import ABC, abstractmethod
from typing import ClassVar
from pathlib import Path

from ddp_backend.schemas import ModelName, VideoReport, STTReport

class VisualDetector(ABC):
    model_name: ClassVar[ModelName]

    @abstractmethod
    def load_model(self):
        pass

    @abstractmethod
    async def analyze(self, vid_path: str | Path) -> VideoReport:
        pass

class AudioAnalyzer(ABC):
    model_name: ClassVar[ModelName]

    @abstractmethod
    async def analyze(self, vid_path: str | Path) -> STTReport:
        pass