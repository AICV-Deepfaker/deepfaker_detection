from collections.abc import Sequence
from pathlib import Path
from typing import cast, final, override

import numpy as np
import onnxruntime as ort  # type: ignore
from torch import Tensor
from torch.utils.data import DataLoader
from unite_detection.dataset import CustomVideoDataset
from unite_detection.schemas import ArchSchema, DatasetConfig

from ddp_backend.schemas.enums import ModelName

from .base import BaseVideoConfig, BaseVideoDetector, VideoInferenceResult


@final
class UniteDetector(BaseVideoDetector[BaseVideoConfig]):
    model_name = ModelName.UNITE

    @override
    def load_model(self):
        self.session = ort.InferenceSession(
            self.config.model_path,
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        self.input_name: str = self.session.get_inputs()[0].name # type: ignore
        self.output_name: str = self.session.get_outputs()[0].name # type: ignore

    @staticmethod
    def softmax(x: np.ndarray) -> np.ndarray:
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum()

    @override
    def _analyze(self, vid_path: str | Path) -> VideoInferenceResult:
        vid_dataset = CustomVideoDataset(
            [vid_path],
            config=DatasetConfig(arch=ArchSchema(img_size=self.config.img_size)),
        )
        loader = DataLoader(vid_dataset, batch_size=1, num_workers=0)
        result_prob: list[float] = []
        for batch in loader:
            x, _ = cast(tuple[Tensor, Tensor], batch)
            input_np: np.ndarray = x.detach().cpu().numpy()
            output = self.session.run([self.output_name], {self.input_name: input_np}) # type: ignore
            output = cast(Sequence[np.ndarray], output)
            cur_prob: float = self.softmax(output[0])[0][1].item()
            result_prob.append(cur_prob)
        max_prob = max(result_prob)
        # currently no visual output
        return VideoInferenceResult(prob=max_prob, base64_report="")
