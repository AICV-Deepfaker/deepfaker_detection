from .clip_detector import CLIPDetector
from .clip_detector_wavelet import CLIPDetectorWavelet
from .registry import DETECTOR

__all__ = ["DETECTOR", "CLIPDetector", "CLIPDetectorWavelet"]