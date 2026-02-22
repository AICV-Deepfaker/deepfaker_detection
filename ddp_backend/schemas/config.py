from pathlib import Path

from pydantic import BaseModel

__all__ = [
    "BaseVideoConfig",
    "WaveletConfig",
]


class BaseVideoConfig(BaseModel):
    model_path: str | Path
    threshold: float = 0.5
    img_size: int


class WaveletConfig(BaseVideoConfig):
    mean: tuple[float, float, float]
    std: tuple[float, float, float]
    model_name: str
    loss_func: str
