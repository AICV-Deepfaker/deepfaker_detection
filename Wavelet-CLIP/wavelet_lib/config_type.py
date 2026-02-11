from typing import TypedDict

class WaveletConfig(TypedDict):
    model_name: str
    mean: tuple[float, float, float]
    std: tuple[float, float, float]
    loss_func: str
