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
from ddp_backend.schemas.report import ProbabilityContent

from .base import BaseVideoConfig, BaseVideoDetector


@final
class UniteDetector(BaseVideoDetector[BaseVideoConfig, ProbabilityContent]):
    model_name = ModelName.UNITE

    @override
    def load_model(self):
        import torch

        sess_options = ort.SessionOptions()
        sess_options.enable_mem_pattern = False
        sess_options.enable_cpu_mem_arena = False

        cuda_available = False
        try:
            cuda_available = ort.get_device() == "GPU"
        except Exception:
            pass

        if cuda_available:
            # CUDA EP 아레나 선점 할당 최소화:
            # - arena_extend_strategy=kSameAsRequested: 필요한 만큼만 할당 (기본값은 큰 블록 선점)
            # - initial_chunk_size_bytes=1MB: 초기 아레나 크기를 최소화해 cublasCreate 실패 방지
            # - gpu_mem_limit: ORT가 사용 가능한 최대 VRAM 제한 (14 GB)
            cuda_provider_options = {
                "device_id": 0,
                "arena_extend_strategy": "kSameAsRequested",
                "initial_chunk_size_bytes": 1 * 1024 * 1024,   # 1 MB
                "gpu_mem_limit": 14 * 1024 * 1024 * 1024,      # 14 GB
                "cudnn_conv_algo_search": "DEFAULT",
                "do_copy_in_default_stream": True,
            }
            # PyTorch 캐시 해제 후 ORT 세션 초기화 (단편화된 VRAM 확보)
            torch.cuda.empty_cache()
            providers: list = [("CUDAExecutionProvider", cuda_provider_options), "CPUExecutionProvider"]
        else:
            providers = ["CPUExecutionProvider"]

        self.session = ort.InferenceSession(
            self.config.model_path,
            sess_options=sess_options,
            providers=providers,
        )
        self.input_name: str = self.session.get_inputs()[0].name  # type: ignore
        self.output_name: str = self.session.get_outputs()[0].name  # type: ignore
        print(f"[UNITE] input shape: {self.session.get_inputs()[0].shape}, providers: {self.session.get_providers()}")

    @staticmethod
    def softmax(x: np.ndarray) -> np.ndarray:
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum()

    @override
    def _analyze(self, vid_path: str | Path) -> ProbabilityContent:
        vid_dataset = CustomVideoDataset(
            [vid_path],
            config=DatasetConfig(arch=ArchSchema(img_size=self.config.img_size)),
        )
        loader = DataLoader(vid_dataset, batch_size=1, num_workers=0)
        result_prob: list[float] = []
        for batch in loader:
            x, _ = cast(tuple[Tensor, Tensor], batch)
            input_np: np.ndarray = x.detach().cpu().numpy()
            output = self.session.run([self.output_name], {self.input_name: input_np})  # type: ignore
            output = cast(Sequence[np.ndarray], output)
            cur_prob: float = self.softmax(output[0])[0][1].item()
            result_prob.append(cur_prob)
        max_prob = max(result_prob)

        # softmax[0][1]은 FAKE 클래스 확률 → ProbabilityContent는 REAL 확률 기대
        return ProbabilityContent(probability=1.0 - max_prob)
