from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from collections.abc import Generator
from pathlib import Path
import torch

import cv2
from pydantic import BaseModel


class Config[S: BaseSetting](BaseModel):
    model_path: str | Path
    img_config: ImageConfig | None = None
    threshold: float = 0.5
    specific_config: S | None = None


class BaseSetting(BaseModel):
    pass


class ImageConfig(BaseModel):
    img_size: int
    mean: tuple[float, float, float] | None = None
    std: tuple[float, float, float] | None = None

class ImageResult(BaseModel):
    prob: float
    base64_report: str

class BaseDetector[Result: BaseModel](ABC):
    @abstractmethod
    def load_model(self):
        pass

    @abstractmethod
    async def _analyze(self, vid_path: str | Path) -> Result:
        pass

    @abstractmethod
    async def analyze(self, vid_path: str | Path) -> dict:
        pass


class BaseVideoDetector[S: BaseSetting](BaseDetector[ImageResult]):
    def __init__(self, config: Config[S]):
        self.config: Config[S] = config
        self.device: torch.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    @contextmanager
    def _load_video(self, vid_path: str | Path) -> Generator[cv2.VideoCapture, None, None]:
        cap = None
        try:
            cap = cv2.VideoCapture(vid_path)
            if not cap.isOpened():
                raise FileNotFoundError(f"File {vid_path} not found.")
            yield cap
        finally:
            if cap is not None:
                cap.release()

    async def analyze(self, vid_path: str | Path) -> dict:
        analyze_res = self._analyze(vid_path)

        res = "FAKE" if analyze_res.prob > 0.5 else "REAL"
        confidence = analyze_res.prob if analyze_res.prob > 0.5 else 1 - analyze_res.prob

        return {
            "result": res,
            "average_fake_prob": round(analyze_res.prob, 4),
            "confidence_score": f"{round(confidence * 100, 2)}%",
            "visual_report": analyze_res.base64_report,
        }


