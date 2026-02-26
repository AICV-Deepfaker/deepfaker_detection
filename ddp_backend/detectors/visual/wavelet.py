import os
import cv2
import yaml
import torch
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from io import BytesIO
from pathlib import Path
from typing import Any, cast, override
from torchvision import transforms as T

# 백엔드 라이브러리 및 스키마
from wavelet_lib.detectors import DETECTOR 
from ddp_backend.schemas.config import WaveletConfig as WaveletConfigParam
from ddp_backend.schemas.enums import ModelName
from ddp_backend.schemas.report import ProbVisualContent
from .base import BaseVideoDetector

class WaveletDetector(BaseVideoDetector[WaveletConfigParam, ProbVisualContent]):
    model_name = ModelName.WAVELET

    @override
    def load_model(self):
        ckpt_path = Path(self.config.model_path)
        if not ckpt_path.exists():
            print(f"[WaveletDetector] 체크포인트를 찾을 수 없습니다: {ckpt_path}")
            self.model = None
            return

        # inference_result.py의 모델 로드 로직 적용
        wavelet_config = {
            "mean": self.config.mean,
            "std": self.config.std,
            "model_name": self.config.model_name,
            "loss_func": self.config.loss_func,
        }
        
        self.model = DETECTOR[self.config.model_name](wavelet_config).to(self.device)
        ckpt = torch.load(self.config.model_path, map_location=self.device)
        state_dict = ckpt.get("state_dict", ckpt.get("model", ckpt))
        state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
        self.model.load_state_dict(state_dict, strict=True)
        self.model.eval()
        print(f"모델 로드 완료: {self.config.model_path}")

    # ==========================================
    # inference_result.py: HH 서브밴드 추출 로직
    # ==========================================
    def get_hh_subband(self, img_rgb, transform, img_size):
        img_resized = cv2.resize(img_rgb, (img_size, img_size))
        tensor = transform(img_resized).unsqueeze(0).to(self.device)

        with torch.no_grad():
            # 모델에 dwt2d가 있다고 가정 (원본 코드 기준)
            _, yh_img = self.model.dwt2d(tensor)
            hh = yh_img[0][:, :, 2, :, :]   # (1, 3, H', W')
            hh = hh.squeeze(0).cpu().numpy()  # (3, H', W')

        hh_vis = np.abs(hh).transpose(1, 2, 0)
        hh_vis = (hh_vis - hh_vis.min()) / (hh_vis.max() - hh_vis.min() + 1e-8)
        return hh_vis

    # ==========================================
    # inference_result.py: 시각화 로직 (6-row 레이아웃)
    # ==========================================
    def visualize_to_bytes(self, video_name, frames_rgb, probs, timestamps, img_size, transform):
        avg_prob = float(np.mean(probs))
        verdict = "FAKE" if avg_prob >= 0.5 else "REAL"
        verdict_col = "#e74c3c" if verdict == "FAKE" else "#2ecc71"
        
        # 대표 프레임 선택 (Fake 확률 높은/낮은 순)
        sorted_idx = np.argsort(probs)
        real_idx = sorted_idx[:4]
        fake_idx = sorted_idx[-4:][::-1]

        fig = plt.figure(figsize=(22, 30))
        fig.suptitle(
            f"Inference Result — {video_name}\n"
            f"Overall Verdict: [{verdict}]  (Fake Prob = {avg_prob:.4f})",
            fontsize=18, fontweight='bold', y=0.99, color=verdict_col
        )
        gs = gridspec.GridSpec(6, 4, figure=fig, hspace=0.5, wspace=0.3, top=0.95, bottom=0.02)

        # Row 0: 판정 배너
        ax_banner = fig.add_subplot(gs[0, :])
        ax_banner.set_facecolor(verdict_col)
        ax_banner.text(0.5, 0.5, f"VERDICT: {verdict} | Avg Prob: {avg_prob:.4f} | Frames: {len(probs)}",
                       transform=ax_banner.transAxes, fontsize=16, fontweight='bold', color='white', va='center', ha='center')
        ax_banner.axis('off')

        # Row 1: 타임라인
        ax_time = fig.add_subplot(gs[1, :])
        ax_time.plot(timestamps, probs, color='steelblue', lw=2, marker='o', markersize=4)
        ax_time.axhline(0.5, color='red', linestyle='--')
        ax_time.set_ylim(0, 1)
        ax_time.set_title("Frame-by-Frame Fake Probability Timeline")

        # Row 2: 히스토그램
        ax_hist = fig.add_subplot(gs[2, :])
        ax_hist.hist(probs, bins=20, range=(0, 1), color='steelblue', alpha=0.7)
        ax_hist.axvline(0.5, color='red', linestyle='--')
        ax_hist.set_title("Distribution of Frame Probabilities")

        # Row 3 & 4: 대표 프레임 (Real / Fake)
        for col, idx in enumerate(real_idx):
            ax = fig.add_subplot(gs[3, col])
            ax.imshow(frames_rgb[idx])
            ax.set_title(f"Real p={probs[idx]:.3f}", color='#27ae60')
            ax.axis('off')

        for col, idx in enumerate(fake_idx):
            ax = fig.add_subplot(gs[4, col])
            ax.imshow(frames_rgb[idx])
            ax.set_title(f"Fake p={probs[idx]:.3f}", color='#c0392b')
            ax.axis('off')

        # Row 5: HH Subband (Fake 대표 프레임 기준)
        for col, idx in enumerate(fake_idx):
            ax = fig.add_subplot(gs[5, col])
            try:
                hh_vis = self.get_hh_subband(frames_rgb[idx], transform, img_size)
                ax.imshow(hh_vis)
                ax.set_title(f"HH Subband", color='#8e44ad')
            except:
                ax.text(0.5, 0.5, "DWT Error", ha='center', va='center')
            ax.axis('off')

        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight')
        plt.close(fig)
        return buf.getvalue()

    # ==========================================
    # 메인 분석 로직 (_analyze)
    # ==========================================
    @override
    def _analyze(self, vid_path: str | Path) -> ProbVisualContent:
        img_size = self.config.img_size
        transform = T.Compose([
            T.ToTensor(),
            T.Normalize(mean=self.config.mean, std=self.config.std)
        ])

        frames_rgb, frame_indices = [], []
        fps = 30.0

        # 1. 영상 로드 및 균등 샘플링 (MAX_FRAMES=32)
        with self._load_video(vid_path) as cap:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            max_frames = 32
            n_sample = min(max_frames, total_frames)
            indices = np.linspace(0, total_frames - 1, n_sample, dtype=int)

            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
                ret, frame = cap.read()
                if ret:
                    frames_rgb.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    frame_indices.append(idx)

        # 2. 추론 수행
        probs = []
        timestamps = []
        for frame, idx in zip(frames_rgb, frame_indices):
            img_resized = cv2.resize(frame, (img_size, img_size))
            tensor = transform(img_resized).unsqueeze(0).to(self.device)
            data = {"image": tensor, "label": torch.tensor([0]).to(self.device)}

            with torch.no_grad():
                out = self.model(data, inference=False)
                # Softmax로 Fake 확률(index 1) 추출
                prob = torch.softmax(out["cls"], dim=1)[:, 1].item()
                probs.append(prob)
                timestamps.append(idx / fps)

        # 3. 결과 집계 및 시각화 리포트 생성
        avg_prob = float(np.mean(probs))
        video_name = os.path.basename(str(vid_path))
        
        # 6단 리포트 생성
        visual_bytes = self.visual_to_bytes(
            video_name, frames_rgb, probs, timestamps, img_size, transform
        )

        return ProbVisualContent(
            probability=avg_prob,
            image=visual_bytes
        )