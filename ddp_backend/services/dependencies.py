"""
Singleton variables used across files
"""

#from ddp_backend.detectors.audio import STTDetector
#from ddp_backend.detectors.visual import RPPGDetector, WaveletDetector # UniteDetector
#from ddp_backend.schemas.config import BaseVideoConfig
##from ddp_backend.services import DetectionPipeline

#DETECTOR_YAML = "Wavelet-CLIP/wavelet_lib/config/detector/detector.yaml"
#CKPT_PATH = "/home/ubuntu/deepfaker_detection/ckpt_best_5.pth"
#IMG_SIZE = 224


# UniteDetector (정밀탐지모드 / deep)
#unite_detector = UniteDetector(
 #   BaseVideoConfig(
  #      model_path="./unite_baseline.onnx",
   #     img_size=384,
   # )
#)

# WaveletDetector (증거수집모드 / fast)
#wavelet_detector = WaveletDetector.from_yaml(DETECTOR_YAML, IMG_SIZE, CKPT_PATH)

#r_ppg_detector = RPPGDetector(BaseVideoConfig(model_path="", img_size=0))

#stt_detector = STTDetector()


#detection_pipeline = DetectionPipeline(
#    unite_detector, wavelet_detector, r_ppg_detector, stt_detector
#)


#def load_all_model():
 #   detection_pipeline.load_all_models()
"""
Singleton variables used across files
"""

from ddp_backend.detectors.audio import STTDetector
from ddp_backend.detectors.visual import RPPGDetector, WaveletDetector
from ddp_backend.schemas.config import BaseVideoConfig
from ddp_backend.services import DetectionPipeline

DETECTOR_YAML = "Wavelet-CLIP/wavelet_lib/config/detector/detector.yaml"
CKPT_PATH = "ckpt/ckpt_best_5.pth"
IMG_SIZE = 224


class _UniteDetectorStub:
    """
    UniteDetector 코드/의존성이 아직 없을 때 서버를 띄우기 위한 임시 대체물.
    실제 deep(정밀탐지) 기능 호출 시에는 NotImplementedError를 발생시킴.
    """
    def load_model(self):
        return None

    def predict(self, *args, **kwargs):
        raise NotImplementedError("UniteDetector is not available (unite_detection module missing).")


# UniteDetector (정밀탐지모드 / deep) - 임시 stub
unite_detector = _UniteDetectorStub()

# WaveletDetector (증거수집모드 / fast)
wavelet_detector = WaveletDetector.from_yaml(DETECTOR_YAML, IMG_SIZE, CKPT_PATH)

r_ppg_detector = RPPGDetector(BaseVideoConfig(model_path="", img_size=0))

stt_detector = STTDetector()

detection_pipeline = DetectionPipeline(
    unite_detector, wavelet_detector, r_ppg_detector, stt_detector
)


def load_all_model():
    detection_pipeline.load_all_models()