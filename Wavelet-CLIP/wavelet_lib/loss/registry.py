from ..metrics.registry import Registry
from .abstract_loss_func import AbstractLossClass

LOSSFUNC = Registry[AbstractLossClass]()