import warnings
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
from insightface.utils.face_align import norm_crop  # type: ignore
from pydantic import TypeAdapter
from torchvision.transforms import v2  # type: ignore
from wavelet_lib.config_type import WaveletConfig  # type: ignore
from wavelet_lib.detectors import DETECTOR  # type: ignore
from wavelet_lib.detectors.base_detector import (  # type: ignore
    AbstractDetector,
    PredDict,
)

from ddp_backend.schemas.config import WaveletConfig as WaveletConfigParam
from ddp_backend.schemas.enums import ModelName
from ddp_backend.schemas.report import ProbVisualContent

from .base import BaseVideoDetector

# ─────────────────────────────────────────────────────────────
# 추론 개선 상수 (inference_result.py 와 동기화)
# ─────────────────────────────────────────────────────────────
_MAX_FRAMES       = 64    # [H] 프레임 수 (32 → 64)
_TEMPERATURE      = 0.3   # [A] Temperature Scaling (T<1 → 확률 분포 샤프닝)
_TTA_ENABLED      = True  # [C] Test-Time Augmentation (flip + brightness)
_FACE_PAD_RATIO   = 0.3   # [D] bbox fallback 패딩 비율
_BLUR_THRESHOLD   = 100   # [G] Laplacian variance < 이 값 → 블러 프레임 제거
_FACE_SCORE_THR   = 0.7   # [G] InsightFace det_score < 이 값 → 저신뢰 제거
_AGGREGATION      = "p75" # [E] 집계 전략: mean / max / p75 / any_frame


class WaveletDetector(BaseVideoDetector[WaveletConfigParam, ProbVisualContent]):
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
        ckpt_path = Path(self.config.model_path)

        if not ckpt_path.exists():
            warnings.warn(
                f"[WaveletDetector] checkpoint not found: {ckpt_path}. "
                "Wavelet detector will be disabled (server will still start)."
            )
            self.model = None
            return

        print(f"Loading on device: {self.device}...")
        wavelet_config: WaveletConfig = {
            "mean": self.config.mean,
            "std": self.config.std,
            "model_name": self.config.model_name,
            "loss_func": self.config.loss_func,
            "backbone_trainable_layers": 4,
            "class_weights": [1.0, 8.0],
        }
        self.model: AbstractDetector = DETECTOR[self.config.model_name](
            config=wavelet_config
        ).to(self.device)
        ckpt: dict[str, Any] = torch.load(
            self.config.model_path, map_location=self.device
        )
        state_dict = ckpt.get("state_dict", ckpt.get("model", ckpt))
        state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
        _ = self.model.load_state_dict(state_dict, strict=False)
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

    # ──────────────────────────────────────────────────────────
    # [B] 얼굴 정렬 / 크롭 헬퍼
    # ──────────────────────────────────────────────────────────
    def _get_aligned_face(self, img_rgb: MatLike) -> MatLike:
        """
        [B] InsightFace kps 기반 정렬 우선, 실패 시 bbox 크롭 fallback.
        img_rgb: RGB numpy array
        """
        faces: list[Face] = self.face_app.get(img_rgb)  # type: ignore
        if not faces:
            return img_rgb

        face = max(
            faces,
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),  # type: ignore
        )

        # norm_crop (5-keypoint alignment)
        if face.kps is not None:
            try:
                aligned = norm_crop(
                    img_rgb, landmark=face.kps, image_size=self.config.img_size
                )
                if aligned is not None:
                    return aligned  # type: ignore
            except Exception:
                pass

        # Fallback: padded bbox crop
        x1, y1, x2, y2 = map(int, face.bbox)  # type: ignore
        h, w = img_rgb.shape[:2]
        pw = int((x2 - x1) * _FACE_PAD_RATIO)
        ph = int((y2 - y1) * _FACE_PAD_RATIO)
        x1 = max(0, x1 - pw)
        y1 = max(0, y1 - ph)
        x2 = min(w, x2 + pw)
        y2 = min(h, y2 + ph)
        crop = img_rgb[y1:y2, x1:x2]
        return crop if crop.size > 0 else img_rgb

    # ──────────────────────────────────────────────────────────
    # [A] Temperature Scaling 단일 추론
    # ──────────────────────────────────────────────────────────
    def _infer_single(
        self,
        img_rgb: MatLike,
        transform: v2.Compose,
        img_size: int,
    ) -> float:
        """단일 RGB 이미지 → fake prob ([A] TEMPERATURE 적용)."""
        resized = cv2.resize(img_rgb, (img_size, img_size))
        img_tensor = cast(torch.Tensor, transform(resized)).unsqueeze(0).to(self.device)
        data_dict = {
            "image": img_tensor,
            "label": torch.zeros(1).long().to(self.device),
        }
        with torch.no_grad():
            pred: PredDict = self.model(data_dict, inference=False)
            prob = torch.softmax(pred["cls"] / _TEMPERATURE, dim=1)[:, 1].item()
        return float(prob)

    # ──────────────────────────────────────────────────────────
    # 시각화 리포트 (기존 유지)
    # ──────────────────────────────────────────────────────────
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
        return buf.getvalue()

    # ──────────────────────────────────────────────────────────
    # 메인 추론 (inference_result.py 개선사항 통합)
    # ──────────────────────────────────────────────────────────
    @override
    def _analyze(self, vid_path: str | Path) -> ProbVisualContent:
        if not hasattr(self, "model") or self.model is None:
            raise RuntimeError("Wavelet model is not loaded (checkpoint not found).")

        img_size = self.config.img_size
        transform = v2.Compose(
            [
                v2.ToImage(),
                v2.ToDtype(torch.float32),
                v2.Normalize(mean=self.config.mean, std=self.config.std),
            ]
        )

        # ── Step 1: [H] 균등 간격 프레임 샘플링 ──────────────
        print("Starting analyze (wavelet)...")
        raw_frames: list[MatLike] = []
        with self._load_video(vid_path) as cap:
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            n_sample = min(_MAX_FRAMES, max(total, 1))
            indices = np.linspace(0, total - 1, n_sample, dtype=int)

            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
                ret, frame = cap.read()
                if ret:
                    raw_frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        if not raw_frames:
            raise RuntimeError

        # ── Step 2: [G] 프레임 품질 필터링 ──────────────────
        valid_frames: list[MatLike] = []
        for rgb in raw_frames:
            # 블러 검사
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            if cv2.Laplacian(gray, cv2.CV_64F).var() < _BLUR_THRESHOLD:
                continue
            # 얼굴 신뢰도 검사
            faces: list[Face] = self.face_app.get(rgb)  # type: ignore
            if not faces:
                continue
            best = max(
                faces,
                key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),  # type: ignore
            )
            if best.det_score < _FACE_SCORE_THR:
                continue
            valid_frames.append(rgb)

        if not valid_frames:
            valid_frames = raw_frames  # fallback: 필터링된 게 없으면 원본 사용

        # ── Step 3: [B]+[C] 얼굴 정렬 + TTA 추론 ────────────
        all_probs: list[float] = []
        max_prob: float = -1.0
        best_face_rgb: MatLike | None = None

        for rgb in valid_frames:
            # [B] 얼굴 정렬 / 크롭
            face_rgb = self._get_aligned_face(rgb)

            # [C] TTA view 구성: 원본 + flip + brightness ×1.1 / ×0.9
            views: list[MatLike] = [face_rgb, cv2.flip(face_rgb, 1)]
            if _TTA_ENABLED:
                views.append(
                    np.clip(face_rgb.astype(np.float32) * 1.1, 0, 255).astype(np.uint8)
                )
                views.append(
                    np.clip(face_rgb.astype(np.float32) * 0.9, 0, 255).astype(np.uint8)
                )

            # 각 view 추론 후 평균
            frame_probs = [self._infer_single(v, transform, img_size) for v in views]
            avg_p = float(np.mean(frame_probs))
            all_probs.append(avg_p)

            if avg_p > max_prob:
                max_prob = avg_p
                best_face_rgb = face_rgb

        if not all_probs:
            raise RuntimeError

        # ── Step 4: [E] p75 집계 ─────────────────────────────
        arr = np.array(all_probs)
        if _AGGREGATION == "mean":
            final_prob = float(np.mean(arr))
        elif _AGGREGATION == "max":
            final_prob = float(np.max(arr))
        elif _AGGREGATION in ("p75", "any_frame"):
            final_prob = float(np.percentile(arr, 75))
        else:
            final_prob = float(np.mean(arr))

        # ── 시각화 리포트 ─────────────────────────────────────
        visual_report = None
        if best_face_rgb is not None:
            visual_report = self.generate_visual_report(best_face_rgb, max_prob)

        return ProbVisualContent(probability=final_prob, image=visual_report)
