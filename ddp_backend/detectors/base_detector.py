from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol, cast, runtime_checkable

import cv2
import torch
from pydantic import BaseModel

from ddp_backend.schemas import BaseReport, VideoReport


class HasPath(BaseModel):
    model_path: str | Path


class HasThreshold(BaseModel):
    threshold: float = 0.5


class HasNormalize(BaseModel):
    mean: tuple[float, float, float]
    std: tuple[float, float, float]


class ImageInferenceResult(BaseModel):
    prob: float
    base64_report: str


class BaseVideoConfig(HasPath, HasThreshold):
    img_size: int


@runtime_checkable
class Scorable(Protocol):
    prob: float


class BaseDetector[Config: BaseModel, Report: BaseReport](ABC):
    model_name: str

    def __init__(self, config: Config):
        self.config = config

    @abstractmethod
    def load_model(self):
        pass

    @abstractmethod
    async def _analyze(self, vid_path: str | Path) -> BaseModel:
        pass

    @abstractmethod
    async def analyze(self, vid_path: str | Path) -> Report:
        pass


class BaseVideoDetector[C: BaseVideoConfig](BaseDetector[C, VideoReport]):
    def __init__(self, config: C):
        super().__init__(config)
        self.device: torch.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

    @contextmanager
    def _load_video(
        self, vid_path: str | Path
    ) -> Generator[cv2.VideoCapture, None, None]:
        cap = None
        try:
            cap = cv2.VideoCapture(vid_path)
            if not cap.isOpened():
                raise FileNotFoundError(f"File {vid_path} not found.")
            yield cap
        finally:
            if cap is not None:
                cap.release()

    def set_fps(self, vid_src: str | Path, vid_dest: str | Path, target_fps: int = 30):
        with self._load_video(vid_src) as cap:
            cap.get(cv2.CAP_PROP_FPS)
            pass

    async def analyze(self, vid_path: str | Path) -> VideoReport:
        analyze_res = cast(ImageInferenceResult, await self._analyze(vid_path))

        res = "FAKE" if analyze_res.prob > 0.5 else "REAL"
        confidence = (
            analyze_res.prob if analyze_res.prob > 0.5 else 1 - analyze_res.prob
        )

        return VideoReport(
            status="success",
            model_name=self.model_name,
            result=res,
            average_fake_prob=round(analyze_res.prob, 4),
            confidence_score=f"{round(confidence * 100, 2)}",
            visual_report=analyze_res.base64_report,
        )
