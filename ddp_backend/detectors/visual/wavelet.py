import base64
from io import BytesIO
from pathlib import Path
from typing import Any, Self, cast, override

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pywt  # type: ignore
import torch
import yaml
from cv2.typing import MatLike
from insightface.app import FaceAnalysis  # type: ignore
from insightface.app.common import Face  # type: ignore
from pydantic import TypeAdapter
from torchvision.transforms import v2  # type: ignore
from wavelet_lib.config_type import WaveletConfig  # type: ignore
from wavelet_lib.detectors import DETECTOR  # type: ignore
from wavelet_lib.detectors.base_detector import (  # type: ignore
    AbstractDetector,
    PredDict,
)

from schemas.enums import ModelName
from schemas.config import WaveletConfig as WaveletConfigParam

from .base import (
    BaseVideoDetector,
    VideoInferenceResult,
)


class WaveletDetector(BaseVideoDetector[WaveletConfigParam]):
    model_name = ModelName.WAVELET

    @classmethod
    def from_yaml(
        cls,
        yaml_path: str | Path,
        img_size: int,
        ckpt_path: str | Path,
        threshold: float = 0.5,
    ) -> Self:
        with open(yaml_path, "r") as f:
            raw_data = yaml.safe_load(f)
            model_config = TypeAdapter(WaveletConfig).validate_python(raw_data)

        new_config = WaveletConfigParam(
            model_path=ckpt_path,
            img_size=img_size,
            mean=model_config["mean"],
            std=model_config["std"],
            threshold=threshold,
            model_name=model_config["model_name"],
            loss_func=model_config["loss_func"],
        )
        return cls(new_config)

    @override
    def load_model(self):
        print(f"Loading on device: {self.device}...")
        wavelet_config: WaveletConfig = {
            "mean": self.config.mean,
            "std": self.config.std,
            "model_name": self.config.model_name,
            "loss_func": self.config.loss_func,
        }
        self.model: AbstractDetector = DETECTOR[self.config.model_name](
            config=wavelet_config
        ).to(self.device)
        ckpt: dict[str, Any] = torch.load(
            self.config.model_path, map_location=self.device
        )
        state_dict = {k.replace("module.", ""): v for k, v in ckpt.items()}
        _ = self.model.load_state_dict(state_dict, strict=True)
        _ = self.model.eval()

        providers = (
            ["CUDAExecutionProvider", "CPUExecutionProvider"]
            if str(self.device) != "cpu"
            else ["CPUExecutionProvider"]
        )

        self.face_app: FaceAnalysis = FaceAnalysis(
            name="buffalo_l",
            providers=providers,
        )
        self.face_app.prepare(ctx_id=0, det_size=(640, 640))  # type: ignore

        print("Load Complete.")

    @staticmethod
    def apply_ycbcr_preprocess(img_rgb: MatLike):
        img_ycrp = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2YCrCb)
        img_ycrp[:, :, 0] = 0
        return img_ycrp

    @staticmethod
    def generate_visual_report(best_img_rgb: MatLike, max_prob: float):
        gray = cv2.cvtColor(best_img_rgb, cv2.COLOR_RGB2GRAY)
        coeffs = pywt.dwt2(gray, "haar")  # type: ignore
        _, (LH, HL, HH) = coeffs  # type: ignore
        energy_map = np.sqrt(LH**2 + HL**2 + HH**2)  # type: ignore
        energy_map: np.ndarray = cv2.normalize(  # type: ignore
            energy_map,
            None,  # type: ignore
            0,
            255,
            cv2.NORM_MINMAX,
        ).astype(np.uint8)

        fig, axes = plt.subplots(1, 2, figsize=(10, 5))  # type: ignore
        axes[0].imshow(best_img_rgb)
        axes[0].set_title(f"Target Face (Prob: {max_prob:.4f})")
        axes[0].axis("off")

        im = axes[1].imshow(energy_map, cmap="magma")
        axes[1].set_title("Wavelet High-Freq Energy Map")
        axes[1].axis("off")
        plt.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04)  # type: ignore

        buf = BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")  # type: ignore
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    @override
    def _analyze(self, vid_path: str | Path) -> VideoInferenceResult:
        all_probs: list[float] = []
        max_prob: float = -1.0
        best_img_for_viz = None

        transform = v2.Compose(
            [
                v2.ToImage(),
                v2.ToDtype(torch.float32),
                v2.Normalize(mean=self.config.mean, std=self.config.std),
            ]
        )
        print("Starting analyze (wavelet)...")
        with self._load_video(vid_path) as cap:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                faces: list[Face] = self.face_app.get(rgb)  # type: ignore

                if len(faces) > 0:
                    face = max(
                        faces,
                        key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),  # pyright: ignore[reportUnknownLambdaType, reportOptionalSubscript]
                    )
                    x1, y1, x2, y2 = map(int, face.bbox)  # pyright: ignore[reportArgumentType]
                    h, w, _ = rgb.shape
                    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
                    face_crop = rgb[y1:y2, x1:x2]
                else:
                    face_crop = rgb

                resized = cv2.resize(
                    face_crop,
                    (self.config.img_size, self.config.img_size),
                )
                processed_img = self.apply_ycbcr_preprocess(resized)

                img_tensor = (
                    cast(torch.Tensor, transform(processed_img))
                    .unsqueeze(0)
                    .to(self.device)
                )
                with torch.no_grad():
                    data_dict = {
                        "image": img_tensor,
                        "label": torch.zeros(1).long().to(self.device),
                    }
                    pred: PredDict = self.model(data_dict, inference=True)
                    prob = pred["prob"].item()
                    all_probs.append(prob)

                    if prob > max_prob:
                        max_prob = prob
                        best_img_for_viz = resized

        avg_prob = np.mean(all_probs) if all_probs else 0.0

        visual_report = ""
        if best_img_for_viz is not None:
            visual_report = self.generate_visual_report(best_img_for_viz, max_prob)

        return VideoInferenceResult(prob=float(avg_prob), base64_report=visual_report)
