import torch.nn as nn
class Registry(object):
    def __init__(self):
        self.data:dict[str, nn.Module] = {}

    def register_module(self, module_name: str|None=None):
        def _register(cls: nn.Module):
            name = module_name
            if name is None:
                name = cls.__class__.__name__
            self.data[name] = cls
            return cls
        return _register

    def __getitem__(self, key: str):
        return self.data[key]

DETECTOR = Registry()
TRAINER  = Registry()
LOSSFUNC = Registry()
