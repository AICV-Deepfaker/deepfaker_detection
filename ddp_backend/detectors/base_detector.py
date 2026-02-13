from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
import torch

import cv2
from pydantic import BaseModel


class Config[S: BaseSetting](BaseModel):
    model_path: str | Path
    img_config: ImageConfig
    threshold: float = 0.5
    specific_config: S


class BaseSetting(BaseModel):
    pass


class ImageConfig(BaseModel):
    img_size: int
    mean: tuple[float, float, float] | None = None
    std: tuple[float, float, float] | None = None


class BaseDetector[S: BaseSetting](ABC):
    def __init__(self, config: Config[S]):
        self.config: Config[S] = config
        self.device: torch.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    @abstractmethod
    def load_model(self):
        pass

    @abstractmethod
    def analyze(self, vid_path: str | Path) -> tuple[float, str]:
        pass

    @contextmanager
    def _load_video(self, vid_path: str | Path):
        cap = None
        try:
            cap = cv2.VideoCapture(vid_path)
            if not cap.isOpened():
                raise FileNotFoundError(f"File {vid_path} not found.")
            yield cap
        finally:
            if cap is not None:
                cap.release()
