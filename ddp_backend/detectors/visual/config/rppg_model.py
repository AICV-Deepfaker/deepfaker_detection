# rppg_model.py
from dataclasses import dataclass
from enum import Enum

# =========
# Model_type
# =========
class ModelType(str, Enum):
    PHYSFORMER = "physformer"
    EFFICIENTPHYS = "efficientphys"

# =========
# Model_config 양식 공통
# =========
@dataclass(frozen=True)
class ModelConfig:
    window_size: int
    img_size: int
    stride: int
    face_crop: bool
    requires_diff: bool


# =========
# rPPG 모델 설정
# =========
class RPPGConfig:
    MIN_FRAMES: int = 160

    CONFIG_MAP = {
        ModelType.PHYSFORMER: ModelConfig(
            window_size=160,
            img_size=128,
            stride=160,
            face_crop=True,
            requires_diff=True,
        ),
        ModelType.EFFICIENTPHYS: ModelConfig(
            window_size=21,
            img_size=72,
            stride=21,
            face_crop=False,
            requires_diff=False,
        ),
    }