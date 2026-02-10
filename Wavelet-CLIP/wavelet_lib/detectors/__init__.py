from ..metrics.registry import DETECTOR

from .clip_detector import CLIPDetector
from .clip_detector_wavelet import CLIPDetectorWavelet

__all__ = ["DETECTOR", "CLIPDetector", "CLIPDetectorWavelet"]