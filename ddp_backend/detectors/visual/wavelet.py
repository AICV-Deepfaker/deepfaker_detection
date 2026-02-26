import warnings
from io import BytesIO
from pathlib import Path
from typing import Any, Self, cast, override

import cv2
import matplotlib.gridspec as gridspec
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
_N_REP_FRAMES     = 4     # 대표 프레임 수 (visualization)


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
            print(f"[WaveletDetector] checkpoint not found at: {ckpt_path.resolve()}")
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
    # [F] 대표 프레임 선택 (inference_result.py: select_representative_frames)
    # ──────────────────────────────────────────────────────────
    @staticmethod
    def _select_representative_frames(
        probs: list[float], n: int = _N_REP_FRAMES
    ) -> tuple[list[int], list[int]]:
        """Fake 확률이 가장 높은 n개(fake_idx) + 낮은 n개(real_idx) 인덱스 반환."""
        n = min(n, len(probs))
        sorted_idx = np.argsort(probs)
        real_idx: list[int] = sorted_idx[:n].tolist()
        fake_idx: list[int] = sorted_idx[-n:][::-1].tolist()
        return real_idx, fake_idx

    # ──────────────────────────────────────────────────────────
    # [I] HH 서브밴드 추출 (inference_result.py: get_hh_subband)
    # ──────────────────────────────────────────────────────────
    def _get_hh_subband(
        self, img_rgb: MatLike, transform: v2.Compose, img_size: int
    ) -> np.ndarray:
        """model.dwt2d로 HH 고주파 서브밴드 추출 → 시각화용 (H', W', 3) 배열 반환."""
        img_resized = cv2.resize(img_rgb, (img_size, img_size))
        tensor = cast(torch.Tensor, transform(img_resized)).unsqueeze(0).to(self.device)
        with torch.no_grad():
            _, yh_img = self.model.dwt2d(tensor)  # type: ignore
            hh = yh_img[0][:, :, 2, :, :].squeeze(0).cpu().numpy()  # (3, H', W')
        hh_vis: np.ndarray = np.abs(hh).transpose(1, 2, 0)  # (H', W', 3)
        hh_vis = (hh_vis - hh_vis.min()) / (hh_vis.max() - hh_vis.min() + 1e-8)
        return hh_vis

    # ──────────────────────────────────────────────────────────
    # 시각화 리포트 (inference_result.py: visualize — 6-panel figure)
    # ──────────────────────────────────────────────────────────
    def generate_visual_report(
        self,
        frames_rgb: list[MatLike],
        all_probs: list[float],
        timestamps: list[float],
        transform: v2.Compose,
        img_size: int,
    ) -> bytes:
        """inference_result.py의 6-row 시각화 figure를 PNG bytes로 반환."""
        probs_arr = np.array(all_probs)
        avg_prob = float(np.mean(probs_arr))
        verdict = "FAKE" if avg_prob >= 0.5 else "REAL"
        verdict_col = "#e74c3c" if verdict == "FAKE" else "#2ecc71"
        n_frames = len(frames_rgb)
        n_rep = min(_N_REP_FRAMES, n_frames)

        real_idx, fake_idx = self._select_representative_frames(all_probs, n=n_rep)

        fig = plt.figure(figsize=(22, 30))  # type: ignore
        fig.suptitle(
            f"Wavelet Inference Result\n"
            f"Overall Verdict: [{verdict}]  (Avg Fake Prob = {avg_prob:.4f})",
            fontsize=18, fontweight="bold", y=0.99, color=verdict_col,
        )
        gs = gridspec.GridSpec(6, 4, figure=fig, hspace=0.5, wspace=0.3, top=0.95, bottom=0.02)

        # ── Row 0: 판정 배너 ──────────────────────────────────────────
        ax_banner = fig.add_subplot(gs[0, :])
        ax_banner.set_facecolor(verdict_col)
        ax_banner.text(
            0.5, 0.5,
            f"VERDICT: {verdict}  |  Avg Fake Probability: {avg_prob:.4f}"
            f"  |  Frames Analyzed: {n_frames}",
            transform=ax_banner.transAxes,
            fontsize=16, fontweight="bold", color="white", va="center", ha="center",
        )
        ax_banner.axis("off")

        # ── Row 1: 프레임별 확률 타임라인 ────────────────────────────
        ts = np.array(timestamps)
        ax_time = fig.add_subplot(gs[1, :])
        ax_time.plot(ts, probs_arr, color="steelblue", lw=2, marker="o", markersize=4, label="Fake Probability")
        ax_time.axhline(0.5, color="red", linestyle="--", lw=1.5, label="Threshold (0.5)")
        ax_time.fill_between(ts, probs_arr, 0.5, where=(probs_arr >= 0.5), alpha=0.25, color="red", label="Fake region")
        ax_time.fill_between(ts, probs_arr, 0.5, where=(probs_arr < 0.5), alpha=0.25, color="green", label="Real region")
        if len(ts) > 1:
            ax_time.set_xlim(ts[0], ts[-1])
        ax_time.set_ylim(0, 1)
        ax_time.set_xlabel("Time (seconds)", fontsize=11)
        ax_time.set_ylabel("Fake Probability", fontsize=11)
        ax_time.set_title("Frame-by-Frame Fake Probability Timeline", fontsize=13)
        ax_time.legend(fontsize=9, loc="upper right")
        ax_time.grid(alpha=0.3)

        # ── Row 2: 확률 분포 히스토그램 ──────────────────────────────
        ax_hist = fig.add_subplot(gs[2, :])
        ax_hist.hist(probs_arr, bins=20, range=(0, 1), color="steelblue", alpha=0.7, edgecolor="white")
        ax_hist.axvline(0.5, color="red", linestyle="--", lw=2, label="Threshold")
        ax_hist.axvline(avg_prob, color="orange", linestyle="-", lw=2, label=f"Mean = {avg_prob:.4f}")
        ax_hist.set_xlabel("Fake Probability", fontsize=11)
        ax_hist.set_ylabel("Frame Count", fontsize=11)
        ax_hist.set_title("Distribution of Frame Probabilities", fontsize=13)
        ax_hist.legend(fontsize=9)
        ax_hist.grid(alpha=0.3)

        # ── Row 3: Real로 분류된 대표 프레임 ─────────────────────────
        for col, idx in enumerate(real_idx):
            ax = fig.add_subplot(gs[3, col])
            ax.imshow(frames_rgb[idx])
            ax.set_title(f"Real  p={all_probs[idx]:.3f}\n@{timestamps[idx]:.1f}s", fontsize=9, color="#27ae60")
            ax.axis("off")

        # ── Row 4: Fake로 분류된 대표 프레임 ─────────────────────────
        for col, idx in enumerate(fake_idx):
            ax = fig.add_subplot(gs[4, col])
            ax.imshow(frames_rgb[idx])
            ax.set_title(f"Fake  p={all_probs[idx]:.3f}\n@{timestamps[idx]:.1f}s", fontsize=9, color="#c0392b")
            ax.axis("off")

        # ── Row 5: HH 고주파 서브밴드 (Fake 대표 프레임) ─────────────
        has_dwt = hasattr(self.model, "dwt2d")
        for col, idx in enumerate(fake_idx):
            ax = fig.add_subplot(gs[5, col])
            if has_dwt:
                try:
                    hh_vis = self._get_hh_subband(frames_rgb[idx], transform, img_size)
                    ax.imshow(hh_vis)
                    ax.set_title(f"HH Subband\n@{timestamps[idx]:.1f}s", fontsize=9, color="#8e44ad")
                except Exception:
                    ax.text(0.5, 0.5, "N/A", ha="center", va="center", transform=ax.transAxes)
            else:
                # model.dwt2d 없으면 pywt fallback
                gray = cv2.cvtColor(frames_rgb[idx], cv2.COLOR_RGB2GRAY)
                _, (LH, HL, HH) = pywt.dwt2(gray, "haar")  # type: ignore
                energy = np.sqrt(LH**2 + HL**2 + HH**2)  # type: ignore
                energy = cv2.normalize(energy, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)  # type: ignore
                ax.imshow(energy, cmap="magma")
                ax.set_title(f"HH Energy\n@{timestamps[idx]:.1f}s", fontsize=9, color="#8e44ad")
            ax.axis("off")

        buf = BytesIO()
        plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")  # type: ignore
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

        # ── Step 1: [H] 균등 간격 프레임 샘플링 (fps + 인덱스 추적) ──────────────
        print("Starting analyze (wavelet)...")
        raw_frames: list[MatLike] = []
        raw_frame_indices: list[int] = []
        fps: float = 30.0
        with self._load_video(vid_path) as cap:
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            n_sample = min(_MAX_FRAMES, max(total, 1))
            indices = np.linspace(0, total - 1, n_sample, dtype=int)

            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
                ret, frame = cap.read()
                if ret:
                    raw_frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    raw_frame_indices.append(int(idx))

        if not raw_frames:
            raise RuntimeError

        # ── Step 2: [G] 프레임 품질 필터링 (인덱스 함께 유지) ──────────────────
        valid_frames: list[MatLike] = []
        valid_frame_indices: list[int] = []
        for rgb, fidx in zip(raw_frames, raw_frame_indices):
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
            valid_frame_indices.append(fidx)

        if not valid_frames:
            valid_frames = raw_frames  # fallback: 필터링된 게 없으면 원본 사용
            valid_frame_indices = raw_frame_indices

        # 타임스탬프 계산 (inference_result.py: timestamps)
        timestamps: list[float] = [idx / fps for idx in valid_frame_indices]

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

        # ── 시각화 리포트 (inference_result.py: visualize와 동일한 인자 사용) ──
        visual_report = None
        if valid_frames and all_probs:
            visual_report = self.generate_visual_report(
                valid_frames,
                all_probs,
                timestamps,
                transform,
                img_size,
            )

        return ProbVisualContent(probability=final_prob, image=visual_report)
