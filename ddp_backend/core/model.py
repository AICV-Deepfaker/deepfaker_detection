"""
Singleton variables used across files
"""

from ddp_backend.detectors.audio import STTDetector
from ddp_backend.detectors.visual import RPPGDetector, UniteDetector, WaveletDetector
from ddp_backend.schemas.config import BaseVideoConfig
from ddp_backend.services import DetectionPipeline

from .config import settings

DETECTOR_YAML = "Wavelet-CLIP/wavelet_lib/config/detector/detector.yaml"
CKPT_PATH = "/home/ubuntu/deepfaker_detection/ckpt_best_5.pth"
IMG_SIZE = 224


# UniteDetector (정밀탐지모드 / deep)
unite_detector = UniteDetector(
    BaseVideoConfig(
        model_path=settings.UNITE_MODEL_PATH,
        img_size=settings.UNITE_IMG_SIZE,
    )
)

# WaveletDetector (증거수집모드 / fast)
wavelet_detector = WaveletDetector.from_yaml(
    settings.WAVELET_YAML_PATH, settings.WAVELET_IMG_SIZE, settings.WAVELET_MODEL_PATH
)

r_ppg_detector = RPPGDetector(
    BaseVideoConfig(
        model_path=settings.RPPG_MODEL_PATH, img_size=settings.RPPG_IMG_SIZE
    )
)

stt_detector = STTDetector()


detection_pipeline = DetectionPipeline(
    unite_detector, wavelet_detector, r_ppg_detector, stt_detector
)


def load_all_model():
    detection_pipeline.load_all_models()
