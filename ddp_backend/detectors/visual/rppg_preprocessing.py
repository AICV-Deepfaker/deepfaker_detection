import cv2
import numpy as np
import torch
from dataclasses import dataclass
from typing import List, Generator
from cv2.typing import MatLike
from insightface.app import FaceAnalysis  # type: ignore
from insightface.app.common import Face  # type: ignore

from ddp_backend.detectors.visual.config import RPPGConfig, FCConfig, ModelType


@dataclass
class PreprocessResult:
    tensors: List[torch.Tensor]
    first_bbox: MatLike | None = None
    last_bbox: MatLike | None = None


class RPPGPreprocessing:

    # =========
    # 1. 기본설정
    # =========
    def __init__(self, model_type: ModelType, img_size: int):
        self.model_type = model_type
        self.model_config = RPPGConfig.CONFIG_MAP[model_type]
        self.min_frames = RPPGConfig.MIN_FRAMES
        self.img_size = img_size
        
        self.face_app = FaceAnalysis(
        name="buffalo_l",
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        self.face_app.prepare(ctx_id=0, det_size=FCConfig.DET_SIZE) # type: ignore

    # =========
    # 2. 프레임 추출
    # =========
    def _extract_frames(self, video_path: str) -> List[np.ndarray]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"비디오 파일을 열 수 없습니다: {video_path}")

        # 프레임 수 먼저 확인 → 부족하면 읽지 않고 None 반환
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames < self.min_frames:
            cap.release()
            raise ValueError(f"프레임 수가 부족합니다. 최소 {self.min_frames}프레임 필요 (현재: {total_frames})")

        frames: List[np.ndarray] = []
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        cap.release()

        return frames

    # =========
    # 3. 윈도우 슬라이싱
    # =========
    def _slice_video(self, frames: List[np.ndarray]) -> Generator[List[np.ndarray], None, None]:
        window_size = self.model_config.window_size
        stride = self.model_config.stride
        total = len(frames)

        fetch_size = window_size + 1 if self.model_config.requires_diff else window_size

        for start in range(0, total - fetch_size + 1, stride):
            yield frames[start : start + fetch_size]

    # =========
    # 4-1. 얼굴 크롭 # 사용성을 위해 주파수 모델과 lib 통일
    # =========
    def _get_aligned_face(self, img_rgb: MatLike, return_bbox: bool = False) -> tuple[MatLike, MatLike | None]:
        h, w = img_rgb.shape[:2]

        faces: list[Face] = self.face_app.get(img_rgb)  # type: ignore
        if not faces:
            return img_rgb, img_rgb if return_bbox else None

        face = max(
            faces,
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),  # type: ignore
        )

        # bbox crop (시작/끝 프레임만)
        bbox_crop = None
        if return_bbox:
            x1, y1, x2, y2 = map(int, face.bbox)  # type: ignore
            pw = int((x2 - x1) * FCConfig.FACE_PAD_RATIO)
            ph = int((y2 - y1) * FCConfig.FACE_PAD_RATIO)
            bx1 = max(0, x1 - pw)
            by1 = max(0, y1 - ph)
            bx2 = min(w, x2 + pw)
            by2 = min(h, y2 + ph)
            crop = img_rgb[by1:by2, bx1:bx2]
            bbox_crop = crop if crop.size > 0 else img_rgb

        # seg crop
        lmk = face.landmark_2d_106.astype(np.int32)  # type: ignore
        face_oval: np.ndarray = lmk[FCConfig.FACE_OVAL_INDICES].astype(np.int32) # type: ignore

        mask = np.zeros((h, w), dtype=np.uint8)
        hull = cv2.convexHull(face_oval) # type: ignore
        cv2.fillPoly(mask, [hull], 255)

        masked = cv2.bitwise_and(img_rgb, img_rgb, mask=mask)

        ys, xs = np.where(mask > 0)
        x1, y1, x2, y2 = xs.min(), ys.min(), xs.max(), ys.max()
        cropped = masked[y1:y2, x1:x2]

        if cropped.size > 0:
            return cropped, bbox_crop

        # seg fallback
        x1, y1, x2, y2 = map(int, face.bbox)  # type: ignore
        pw = int((x2 - x1) * FCConfig.FACE_PAD_RATIO)
        ph = int((y2 - y1) * FCConfig.FACE_PAD_RATIO)
        bx1 = max(0, x1 - pw)
        by1 = max(0, y1 - ph)
        bx2 = min(w, x2 + pw)
        by2 = min(h, y2 + ph)
        crop = img_rgb[by1:by2, bx1:bx2]
        return crop if crop.size > 0 else img_rgb, bbox_crop
    def _resize_frames(self, frames: List[np.ndarray]) -> List[np.ndarray]:
        resized: List[np.ndarray] = []
        for f in frames:
            if f is None or f.size == 0:
                continue
            # RGB 상태 유지, (W,H) = (size,size)
            resized.append(cv2.resize(f, (self.img_size, self.img_size), interpolation=cv2.INTER_AREA))
        if not resized:
            raise ValueError("All frames are empty after resizing.")
        return resized
    
    # =========
    # 4-2. 정규화 [0, 1]
    # =========
    def _normalize(self, frames: List[np.ndarray]) -> np.ndarray:
        video = np.stack(frames, axis=0).astype(np.float32)  # (T, H, W, C)
        return video / 255.0

    # =========
    # 4-3. 정규화 차분 (PhysFormer용)
    # =========
    def _apply_diff(self, video: np.ndarray, eps: float = 1e-7) -> np.ndarray:
        # (t - t-1) / (t + t-1 + eps) → shape: (T-1, H, W, C)
        t      = video[1:]   # 현재 프레임
        t_prev = video[:-1]  # 이전 프레임
        return (t - t_prev) / (t + t_prev + eps)

    # =========
    # 4-4. Tensor 변환
    # =========
    def _to_tensor(self, video: np.ndarray) -> torch.Tensor:
        # (T, H, W, C) → (C, T, H, W)
        return torch.from_numpy(video).permute(3, 0, 1, 2).float() # type: ignore

    # =========
    # 5. 전체 파이프라인
    # =========
    def process_video(self, video_path: str) -> PreprocessResult:
        frames = self._extract_frames(video_path)
        tensors: List[torch.Tensor] = []
        first_bbox_vis: MatLike | None = None
        last_bbox_vis: MatLike | None = None

        for window in self._slice_video(frames):
            if self.model_config.face_crop:
                first_seg, first_bbox = self._get_aligned_face(window[0], return_bbox=True)
                last_seg, last_bbox = self._get_aligned_face(window[-1], return_bbox=True)
                mid = [self._get_aligned_face(f)[0] for f in window[1:-1]]
                window = [first_seg] + mid + [last_seg]

                 # 시각화용 bbox (윈도우 첫프레임, 윈도우 끝프레임)
                if first_bbox_vis is None and first_bbox is not None:
                    first_bbox_vis = first_bbox
                if last_bbox_vis is None and last_bbox is not None:
                    last_bbox_vis = last_bbox

            window = self._resize_frames(window)

            window = self._normalize(window)
            requires_diff = self.model_config.requires_diff

            if self.model_type == ModelType.EFFICIENTPHYS:
                requires_diff = False

            if requires_diff:
                window = self._apply_diff(window)

            tensor = self._to_tensor(window)
            tensors.append(tensor)

        return PreprocessResult(
            tensors=tensors,
            first_bbox=first_bbox_vis,
            last_bbox=last_bbox_vis,
        )
