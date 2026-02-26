from pathlib import Path
from ddp_backend.schemas.enums import ModelName
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


class RPPGConfigParam(BaseModel):
    model_path: str | Path
    img_size: int = 72
    model_name: ModelName = ModelName.R_PPG
