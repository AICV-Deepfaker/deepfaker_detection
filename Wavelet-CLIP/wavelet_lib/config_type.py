from typing import TypedDict, NotRequired


class WaveletConfig(TypedDict):
    model_name: str
    mean: tuple[float, float, float]
    std: tuple[float, float, float]
    loss_func: str
    backbone_trainable_layers: NotRequired[int]
    class_weights: NotRequired[list[float] | None]
