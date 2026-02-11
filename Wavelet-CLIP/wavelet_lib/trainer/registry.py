from ..metrics.registry import Registry
from .base_trainer import BaseTrainer

TRAINER = Registry[BaseTrainer]()