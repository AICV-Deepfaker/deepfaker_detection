from ..metrics.registry import Registry
from .base_detector import AbstractDetector

DETECTOR = Registry[AbstractDetector]()