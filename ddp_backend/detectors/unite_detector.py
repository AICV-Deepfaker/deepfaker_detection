from pathlib import Path
from typing import cast, override

import numpy as np
import onnxruntime as ort
from torch import Tensor
from torch.utils.data import DataLoader
from unite_detection.dataset import CustomVideoDataset

from .base_detector import BaseDetector, BaseSetting


class UniteDetector(BaseDetector[BaseSetting]):
    @override
    def load_model(self):
        self.session = ort.InferenceSession(
            self.config.model_path,
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    @staticmethod
    def softmax(x: np.ndarray) -> np.ndarray:
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum()

    @override
    def analyze(self, vid_path: str | Path) -> tuple[float, str]:
        vid_dataset = CustomVideoDataset([vid_path])
        loader = DataLoader(vid_dataset, batch_size=1, num_workers=0)
        results: list[np.ndarray] = []
        for batch in loader:
            x, _ = cast(tuple[Tensor, Tensor], batch)
            input_np: np.ndarray = x.detach().cpu().numpy()
            output: list[np.ndarray] = self.session.run(
                [self.output_name], {self.input_name: input_np}
            )
            results.append(output[0])
        res_concat = np.concatenate(results, axis=0)
        res_mean: np.ndarray = np.mean(res_concat, axis=0)
        prob: float = self.softmax(res_mean)[1].item()
        # currently no visual output
        return prob, ""
