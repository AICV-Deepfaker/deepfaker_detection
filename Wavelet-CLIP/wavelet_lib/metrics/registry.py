from wavelet_lib.detectors.base_detector import AbstractDetector
from wavelet_lib.loss.abstract_loss_func import AbstractLossClass

type RegistryType = AbstractDetector | AbstractLossClass
class Registry[T: RegistryType](object):
    def __init__(self):
        self.data:dict[str, type[T]] = {}

    def register_module(self, module_name: str|None=None):
        def _register(cls: type[T]):
            name = module_name
            if name is None:
                name = cls.__name__
            self.data[name] = cls
            return cls
        return _register

    def __getitem__(self, key: str):
        return self.data[key]

DETECTOR = Registry[AbstractDetector]()
TRAINER  = Registry()
LOSSFUNC = Registry[AbstractLossClass]()
