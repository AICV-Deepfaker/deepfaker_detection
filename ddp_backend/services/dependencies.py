"""
Singleton variables used across files
"""

from detectors.audio import STTDetector
from detectors.visual import RPPGDetector, UniteDetector, WaveletDetector
from schemas.config import BaseVideoConfig
from services import DetectionPipeline

DETECTOR_YAML = "/content/deepfaker_detection/Wavelet-CLIP/wavelet_lib/config/detector/detector.yaml"
CKPT_PATH = "ddp_backend/ckpt_best.pth"
IMG_SIZE = 224


# UniteDetector (정밀탐지모드 / deep)
unite_detector = UniteDetector(
    BaseVideoConfig(
        model_path="./unite_baseline.onnx",
        img_size=384,
    )
)

# WaveletDetector (증거수집모드 / fast)
wavelet_detector = WaveletDetector.from_yaml(DETECTOR_YAML, IMG_SIZE, CKPT_PATH)

r_ppg_detector = RPPGDetector(BaseVideoConfig(model_path="", img_size=0))

stt_detector = STTDetector()


detection_pipeline = DetectionPipeline(
    unite_detector, wavelet_detector, r_ppg_detector, stt_detector
)


def load_all_model():
    detection_pipeline.load_all_models()
