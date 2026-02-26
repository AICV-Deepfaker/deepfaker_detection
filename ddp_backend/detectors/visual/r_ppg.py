import warnings
from io import BytesIO
from pathlib import Path
from typing import final, override

import matplotlib.pyplot as plt
import numpy as np
import torch

from ddp_backend.schemas.enums import ModelName
from ddp_backend.detectors.visual.r_ppg import RPPGPreprocessing

from .base import BaseVideoConfig, BaseVideoDetector, VideoInferenceResult



@final
class RPPGDetector(BaseVideoDetector[BaseVideoConfig]):
    model_name = ModelName.R_PPG

    preprocessing = RPPGPreprocessing # RPPG 최소 프레임이 안될 경우 분기처리 필요

    @override
    def load_model(self):
        pass

    @override
    def _analyze(self, vid_path: str | Path) -> VideoInferenceResult:



        
        return VideoInferenceResult(prob=0)


