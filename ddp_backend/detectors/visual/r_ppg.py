import warnings
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Self, override
from collections import OrderedDict

import cv2
import matplotlib
matplotlib.use("Agg")  # 백엔드 환경 GUI 스레드 충돌 방지
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from scipy.signal import welch

#  모듈 임포트
from ddp_backend.schemas.enums import ModelName
from ddp_backend.detectors.visual.models.rppg_preprocessing import RPPGPreprocessing, PreprocessResult
from ddp_backend.detectors.visual.config import ModelType
from .base import BaseVideoDetector, VideoInferenceResult
from ddp_backend.detectors.visual.models.efficientphys_toolbox import EfficientPhys
# 스키마
from ddp_backend.schemas.config import RPPGConfigParam

# ─────────────────────────────────────────────────────────────
# rPPG 추론 상수
# ─────────────────────────────────────────────────────────────
_FS           = 30.0    # 샘플링 주파수
_HR_LOW       = 0.7     # 심박수 유효 대역 (Hz)
_HR_HIGH      = 2.5     # 심박수 유효 대역 (Hz)

class RPPGDetector(BaseVideoDetector[RPPGConfigParam]):
    model_name = ModelName.R_PPG

    @classmethod
    def from_yaml(
        cls,
        yaml_path: str | Path,
        img_size: int,
        ckpt_path: str | Path,
        threshold: float = 0.5,
    ) -> Self:
        new_config = RPPGConfigParam(
            model_path=ckpt_path,
            img_size=img_size,
        )
        return cls(new_config)

    @override
    def load_model(self):
        pth_path = Path(self.config.model_path)

        if not pth_path.exists():
            warnings.warn("RPPG Checkpoints not found. Detector disabled.")
            self.model = None
            return

        print(f"[{self.__class__.__name__}] Loading EfficientPhys on device: {self.device}...")

        self.model = EfficientPhys(frame_depth=10, img_size=self.config.img_size)
        state = torch.load(pth_path, map_location=self.device)  # 보통 OrderedDict
        if isinstance(state, dict) and ("state_dict" in state or "model_state_dict" in state):
            state = state.get("model_state_dict", state.get("state_dict"))  # type: ignore

        state = {k.replace("module.", "", 1): v for k, v in state.items()}  # module. 제거
        self.model.load_state_dict(state, strict=True)  # ✅ 여기서 에러 안 나야 진짜 성공
        self.model.to(self.device)
        self.model.eval()

        self.preprocessor = RPPGPreprocessing(
            model_type=ModelType.EFFICIENTPHYS,
            img_size=self.config.img_size,
        )

        print(f"[{self.__class__.__name__}] Load Complete.")

    def _extract_rppg_features(self, tensors: List[torch.Tensor]) -> tuple[List[np.ndarray], List[Dict[str, float]]]:
        signals = []
        feat_dicts = []
        n_segment = 10 

        with torch.no_grad():
            for tensor in tensors:
                # tensor: (C, T, H, W)
                tensor = tensor.to(self.device)
                C, T, H, W = tensor.shape

                # EfficientPhys 내부 diff로 T-1이 되므로, (T-1)이 n_segment(10) 배수가 되게 T를 패딩
                rem = (T - 1) % n_segment
                if rem != 0 and T > 1:
                    pad = n_segment - rem
                    pad_frame = tensor[:, -1:, :, :].expand(C, pad, H, W)  # (C, pad, H, W)
                    tensor = torch.cat([tensor, pad_frame], dim=1)         # (C, T+pad, H, W)
                    T = tensor.shape[1]

                    # EfficientPhys는 보통 (B, C, T, H, W) 입력을 기대
                x = tensor.unsqueeze(0)  # (1, C, T, H, W)

                out = self.model(x)
                if isinstance(out, (tuple, list)):
                    out = out[0]

                rppg = out.squeeze().detach().cpu().numpy()

                # 원래 길이 기준으로 자르기 (내부 diff 때문에 -1)
                orig_len = max(1, min(rppg.shape[0], (tensor.shape[1] - 1)))
                signal = rppg[:orig_len]
                signals.append(signal)

                freqs, psd = welch(signal, fs=_FS, nperseg=min(len(signal), 256))
                hr_mask = (freqs >= _HR_LOW) & (freqs <= _HR_HIGH)
                
                hr_psd = psd[hr_mask]
                if hr_psd.size > 0:
                    peak_idx = int(np.argmax(hr_psd))
                    dom_freq = freqs[hr_mask][peak_idx]
                    snr = hr_psd.sum() / (psd[~hr_mask].sum() + 1e-8)
                else:
                    dom_freq, snr = 0.0, 0.0

                feat_dicts.append({
                    "dominant_freq": float(dom_freq),
                    "snr": float(snr),
                })

        return signals, feat_dicts

    @staticmethod
    def generate_visual_report(
        tensors: List[torch.Tensor], 
        signals: List[np.ndarray],
        feat_dicts: List[Dict[str, float]]
    ) -> bytes:
        snrs = [fd["snr"] for fd in feat_dicts]
        
        best_idx = int(np.argmax(snrs))
        worst_idx = int(np.argmin(snrs))

        # 레이아웃: 위쪽은 사진 2장, 아래쪽은 길게 뻗은 주파수 그래프 1개
        fig = plt.figure(figsize=(10, 8))
        fig.suptitle("rPPG Blood Volume Pulse Analysis", fontsize=18, fontweight="bold")

        # 1. 가장 높은 SNR 얼굴 사진 (Top-Left)
        ax1 = plt.subplot(2, 2, 1)
        mid_t_best = tensors[best_idx].shape[1] // 2
        img_best = tensors[best_idx][:, mid_t_best, :, :].permute(1, 2, 0).cpu().numpy()
        img_best = np.clip(img_best, 0.0, 1.0)
        ax1.imshow(img_best)
        ax1.set_title(f"Highest SNR: {snrs[best_idx]:.3f}\n(Window #{best_idx})", fontsize=12, fontweight="bold")
        ax1.axis("off")

        # 2. 가장 낮은 SNR 얼굴 사진 (Top-Right)
        ax2 = plt.subplot(2, 2, 2)
        mid_t_worst = tensors[worst_idx].shape[1] // 2
        img_worst = tensors[worst_idx][:, mid_t_worst, :, :].permute(1, 2, 0).cpu().numpy()
        img_worst = np.clip(img_worst, 0.0, 1.0)
        ax2.imshow(img_worst)
        ax2.set_title(f"Lowest SNR: {snrs[worst_idx]:.3f}\n(Window #{worst_idx})", fontsize=12, fontweight="bold")
        ax2.axis("off")

        # 3. 전체 혈류 데이터 Frequency 그래프 (Bottom Wide)
        ax3 = plt.subplot(2, 1, 2)
        # 전체 신호를 이어 붙여서 전체 영상의 혈류 주파수 특성을 확인
        full_signal = np.concatenate(signals)
        f_axis, psd = welch(full_signal, fs=_FS, nperseg=min(len(full_signal), 256))
        
        ax3.plot(f_axis, psd, color="#16a34a", lw=1.5)
        ax3.axvspan(_HR_LOW, _HR_HIGH, alpha=0.15, color="#facc15", label="HR band (0.7-2.5Hz)")
        
        # 주파수 밴드 내 Dominant Frequency 찾기
        hr_mask = (f_axis >= _HR_LOW) & (f_axis <= _HR_HIGH)
        hr_psd = psd[hr_mask]
        if hr_psd.size > 0:
            dom_f = f_axis[hr_mask][np.argmax(hr_psd)]
            ax3.axvline(dom_f, color="red", lw=1.5, linestyle="--", label=f"Dominant: {dom_f:.2f} Hz ({dom_f*60:.0f} BPM)")

        ax3.set_title("Overall Frequency Graph (PSD)", fontsize=14, fontweight="bold")
        ax3.set_xlabel("Frequency [Hz]", fontsize=11)
        ax3.set_ylabel("Power", fontsize=11)
        ax3.set_xlim(0, 4) # 심박수 대역이 잘 보이도록 4Hz까지만 표시
        ax3.legend(loc="upper right", fontsize=10)

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        buf = BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        return buf.getvalue()

    @override
    def _analyze(self, vid_path: str | Path) -> VideoInferenceResult:
        if self.model is None:
            raise RuntimeError("EfficientPhys model is not loaded.")

        print(f"Starting analyze (rPPG Signal Extraction) for {vid_path}...")

        try:
            prep_result: PreprocessResult = self.preprocessor.process_video(str(vid_path))
        except Exception as e:
            warnings.warn(f"[RPPGDetector] Preprocessing failed: {e}")
            raise RuntimeError(f"Preprocessing failed: {str(e)}")

        if not prep_result.tensors:
            raise RuntimeError("No valid face windows extracted.")

        # rPPG 추출 및 시각화용 데이터 획득
        signals, feat_dicts = self._extract_rppg_features(prep_result.tensors)

        # 3포인트 시각화 (최고/최저 SNR 얼굴 + 전체 Frequency 그래프)
        visual_report = self.generate_visual_report(prep_result.tensors, signals, feat_dicts)

        return VideoInferenceResult(prob=0.0, image=visual_report)