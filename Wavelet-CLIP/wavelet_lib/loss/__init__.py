from .cross_entropy_loss import CrossEntropyLoss
from .focal_loss import FocalLoss, WeightedCrossEntropyLoss
from .registry import LOSSFUNC

__all__ = ['LOSSFUNC', 'CrossEntropyLoss', 'FocalLoss', 'WeightedCrossEntropyLoss']