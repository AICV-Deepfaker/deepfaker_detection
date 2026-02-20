from collections.abc import Sequence
from pathlib import Path
from typing import cast, override

import numpy as np
import onnxruntime as ort
from torch import Tensor
from torch.utils.data import DataLoader
from unite_detection.dataset import CustomVideoDataset
from unite_detection.schemas import ArchSchema, DatasetConfig

from .base_detector import BaseVideoConfig, BaseVideoDetector, ImageInferenceResult


class UniteDetector(BaseVideoDetector[BaseVideoConfig]):
    @override
    def load_model(self):
        self.session = ort.InferenceSession(
            self.config.model_path,
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        self.input_name: str = self.session.get_inputs()[0].name
        self.output_name: str = self.session.get_outputs()[0].name

    @staticmethod
    def softmax(x: np.ndarray) -> np.ndarray:
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum()

    @override
    async def _analyze(self, vid_path: str | Path) -> ImageInferenceResult:
        vid_dataset = CustomVideoDataset(
            [vid_path],
            config=DatasetConfig(arch=ArchSchema(img_size=self.config.img_size)),
        )
        loader = DataLoader(vid_dataset, batch_size=1, num_workers=0)
        result_prob: list[float] = []
        for batch in loader:
            x, _ = cast(tuple[Tensor, Tensor], batch)
            input_np: np.ndarray = x.detach().cpu().numpy()
            output = self.session.run([self.output_name], {self.input_name: input_np})
            output = cast(Sequence[np.ndarray], output)
            cur_prob: float = self.softmax(output[0])[0][1].item()
            result_prob.append(cur_prob)
        max_prob = max(result_prob)
        # currently no visual output
        return ImageInferenceResult(prob=max_prob, base64_report="")
