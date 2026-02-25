# ddp_backend/detectors/visual/r_ppg_preprocessing.py
"""
RPPGPreprocessing
-----------------
OpenCV 기반 영상 전처리.
출력: dict {"frames", "tensor", "fps", "is_bgr"}
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import TypedDict

import numpy as np
import torch

_INPUT_FRAMES: int = 21
_DEFAULT_IMG_SIZE: int = 128


class PreprocessResult(TypedDict):
    frames: list[np.ndarray]  # (H, W, 3) uint8 RGB
    tensor: torch.Tensor      # (1, 3, T, H, W) float32
    fps: float
    is_bgr: bool              # always False – frames are RGB


class RPPGPreprocessing:
    """
    Parameters
    ----------
    vid_path : str | Path
    n_frames : int   균등 샘플링 프레임 수 (default: _INPUT_FRAMES = 21)
    img_size : int   리사이즈 해상도 (정방형, default: 128)
    """

    def __init__(
        self,
        vid_path: str | Path,
        n_frames: int = _INPUT_FRAMES,
        img_size: int = _DEFAULT_IMG_SIZE,
    ) -> None:
        self.vid_path = Path(vid_path)
        self.n_frames = n_frames
        self.img_size = img_size

    # ------------------------------------------------------------------
    def __call__(self) -> PreprocessResult:
        return self.run()

    # ------------------------------------------------------------------
    def run(self) -> PreprocessResult:
        """
        Returns
        -------
        PreprocessResult
            frames : list[(H,W,3) uint8 RGB]
            tensor : (1, 3, T, H, W) float32  range [0,1]
            fps    : float
            is_bgr : False
        """
        try:
            import cv2  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "[RPPGPreprocessing] opencv-python is required. "
                "pip install opencv-python"
            ) from exc

        if not self.vid_path.exists():
            raise FileNotFoundError(
                f"[RPPGPreprocessing] Video file not found: {self.vid_path}"
            )

        cap = cv2.VideoCapture(str(self.vid_path))
        if not cap.isOpened():
            raise RuntimeError(
                f"[RPPGPreprocessing] cv2.VideoCapture failed: {self.vid_path}"
            )

        try:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = float(cap.get(cv2.CAP_PROP_FPS))

            if fps <= 0 or fps > 240:
                warnings.warn(
                    f"[RPPGPreprocessing] Unusual fps={fps:.2f}, defaulting to 30.0.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                fps = 30.0

            if total_frames <= 0:
                warnings.warn(
                    "[RPPGPreprocessing] CAP_PROP_FRAME_COUNT=0; "
                    "falling back to sequential count.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                total_frames = self._count_frames_sequential(cap)
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            if total_frames <= 0:
                raise RuntimeError(
                    f"[RPPGPreprocessing] No readable frames in: {self.vid_path}"
                )

            n = min(self.n_frames, total_frames)
            if n < self.n_frames:
                warnings.warn(
                    f"[RPPGPreprocessing] Only {total_frames} frames available; "
                    f"requested {self.n_frames} → using {n}.",
                    RuntimeWarning,
                    stacklevel=2,
                )

            sample_indices: list[int] = np.linspace(
                0, total_frames - 1, n, dtype=int
            ).tolist()

            blank = np.zeros(
                (self.img_size, self.img_size, 3), dtype=np.uint8
            )
            frames_rgb: list[np.ndarray] = []

            for frame_idx in sample_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, float(frame_idx))
                ret, bgr = cap.read()
                if not ret or bgr is None:
                    warnings.warn(
                        f"[RPPGPreprocessing] Frame {frame_idx} unreadable; "
                        "duplicating previous frame.",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                    frames_rgb.append(
                        frames_rgb[-1].copy() if frames_rgb else blank.copy()
                    )
                    continue

                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                rgb = cv2.resize(
                    rgb,
                    (self.img_size, self.img_size),
                    interpolation=cv2.INTER_AREA,
                )
                frames_rgb.append(rgb)

        finally:
            cap.release()

        if not frames_rgb:
            raise RuntimeError(
                f"[RPPGPreprocessing] Zero frames extracted from: {self.vid_path}"
            )

        # Build tensor: (1, 3, T, H, W) float32 [0, 1]
        arr = np.stack(frames_rgb, axis=0).astype(np.float32) / 255.0  # (T,H,W,3)
        tensor = torch.from_numpy(arr)             # (T, H, W, 3)
        tensor = tensor.permute(3, 0, 1, 2)        # (3, T, H, W)
        tensor = tensor.unsqueeze(0)               # (1, 3, T, H, W)

        return PreprocessResult(
            frames=frames_rgb,
            tensor=tensor,
            fps=fps,
            is_bgr=False,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _count_frames_sequential(cap) -> int:  # type: ignore[no-untyped-def]
        count = 0
        while cap.read()[0]:
            count += 1
        return max(count, 1)