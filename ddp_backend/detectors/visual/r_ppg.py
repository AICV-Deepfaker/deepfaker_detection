# ddp_backend/detectors/rppg_detector.py

# ddp_backend/detectors/rppg_detector.py
"""
RPPGDetector
------------
EfficientPhys rPPG 추출 + XGBoost 분류 기반 딥페이크 탐지기.
"""
from __future__ import annotations

import warnings
from io import BytesIO
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

# ── @final / @override 호환성 ─────────────────────────────────────────────
try:
    from typing import final, override
except ImportError:
    try:
        from typing_extensions import final, override  # type: ignore[assignment]
    except ImportError:
        def final(c):   return c          # type: ignore[misc]
        def override(f): return f         # type: ignore[misc]

# ── SciPy (optional) ─────────────────────────────────────────────────────
try:
    from scipy.signal import welch as _sp_welch, detrend as _sp_detrend  # type: ignore
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False
    warnings.warn(
        "[RPPGDetector] scipy not found – falling back to NumPy FFT PSD.",
        ImportWarning,
        stacklevel=1,
    )


def _detrend(x: np.ndarray) -> np.ndarray:
    if _HAS_SCIPY:
        return _sp_detrend(x).astype(np.float32)
    t = np.arange(len(x), dtype=np.float32)
    A = np.column_stack([t, np.ones_like(t)])
    coef, *_ = np.linalg.lstsq(A, x.astype(np.float32), rcond=None)
    return (x.astype(np.float32) - A @ coef)


def _welch(x: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    if _HAS_SCIPY:
        nperseg = min(len(x), 256)
        f, p = _sp_welch(x, fs=fs, nperseg=nperseg)
        return f.astype(np.float32), p.astype(np.float32)
    n = len(x)
    win = np.hanning(n).astype(np.float32)
    fft = np.fft.rfft(x.astype(np.float32) * win)
    psd = (np.abs(fft) ** 2) / (fs * (win ** 2).sum() + 1e-12)
    freqs = np.fft.rfftfreq(n, d=1.0 / fs).astype(np.float32)
    return freqs, psd


# ── EfficientPhys 다중 경로 import ────────────────────────────────────────
_EFFPHYS_CANDIDATES = [
    ("neural_methods.model.EfficientPhys",              "EfficientPhys"),
    ("rppg_toolbox.neural_methods.model.EfficientPhys", "EfficientPhys"),
    ("model.EfficientPhys",                             "EfficientPhys"),
    ("EfficientPhys",                                   "EfficientPhys"),
]
_EfficientPhysClass: type | None = None
for _mp, _cn in _EFFPHYS_CANDIDATES:
    try:
        import importlib as _il
        _m = _il.import_module(_mp)
        _EfficientPhysClass = getattr(_m, _cn)
        break
    except (ImportError, AttributeError):
        continue

if _EfficientPhysClass is None:
    warnings.warn(
        "[RPPGDetector] EfficientPhys could not be imported from any known path. "
        "Add the model package to PYTHONPATH. Detector will be disabled.",
        ImportWarning,
        stacklevel=1,
    )


# ── XGBoost 로더 ──────────────────────────────────────────────────────────
def _load_xgb(path: Path):
    if not path.exists():
        warnings.warn(
            f"[RPPGDetector] XGBoost model file not found: {path}",
            RuntimeWarning,
            stacklevel=3,
        )
        return None
    try:
        import joblib  # type: ignore
        return joblib.load(path)
    except Exception:
        pass
    try:
        import xgboost as xgb  # type: ignore
        bst = xgb.Booster()
        bst.load_model(str(path))
        return bst
    except Exception as exc:
        warnings.warn(
            f"[RPPGDetector] All XGBoost loaders failed for {path}: {exc}",
            RuntimeWarning,
            stacklevel=3,
        )
        return None


def _xgb_n_features(model) -> int | None:
    for attr in ("n_features_in_", "num_features"):
        if hasattr(model, attr):
            return int(getattr(model, attr))
    try:
        return int(model.num_features())
    except Exception:
        return None


def _xgb_predict(model, X: np.ndarray) -> np.ndarray:
    """Return 1-D fake-prob array, shape (N,)."""
    try:
        return model.predict_proba(X)[:, 1].astype(np.float32)
    except AttributeError:
        pass
    try:
        import xgboost as xgb  # type: ignore
        dm = xgb.DMatrix(X)
        raw = model.predict(dm)
        if raw.ndim == 2:
            return raw[:, 1].astype(np.float32)
        # sigmoid guard
        if raw.max() > 1.0 or raw.min() < 0.0:
            raw = 1.0 / (1.0 + np.exp(-raw))
        return raw.astype(np.float32)
    except Exception as exc:
        raise RuntimeError(f"[RPPGDetector] XGBoost predict failed: {exc}") from exc


# ── 텐서 shape 정규화 → (1, 3, T, H, W) ──────────────────────────────────
def _canonical_tensor(t: torch.Tensor) -> torch.Tensor:
    """
    지원 입력:
      (T, H, W, 3), (T, 3, H, W), (3, T, H, W),
      (1, T, 3, H, W), (1, 3, T, H, W)
    """
    ndim = t.ndim
    if ndim == 3:                        # (T, H, W) greyscale
        t = t.unsqueeze(1).expand(-1, 3, -1, -1).unsqueeze(0)
    elif ndim == 4:
        if t.shape[-1] == 3:             # (T, H, W, 3)
            t = t.permute(3, 0, 1, 2).unsqueeze(0)   # → (1,3,T,H,W)
        elif t.shape[0] == 3:            # (3, T, H, W)
            t = t.unsqueeze(0)
        else:                            # (T, 3, H, W)
            t = t.permute(1, 0, 2, 3).unsqueeze(0)
    elif ndim == 5:
        if t.shape[2] == 3:              # (1, T, 3, H, W)
            t = t.permute(0, 2, 1, 3, 4)
        # else (1, 3, T, H, W) – already canonical
    else:
        raise ValueError(
            f"[RPPGDetector] Cannot canonicalise tensor shape={tuple(t.shape)}"
        )
    return t.float()


# ── rPPG 신호 → 1-D ndarray ──────────────────────────────────────────────
def _to_signal(raw: torch.Tensor) -> np.ndarray:
    arr = raw.detach().cpu().float().numpy()
    if arr.ndim >= 2:
        arr = arr[0].ravel()
    if arr.ndim == 0:
        arr = arr.reshape(1)
    if len(arr) == 0:
        raise ValueError("[RPPGDetector] EfficientPhys returned empty output.")
    return arr.astype(np.float32)


# ── Feature 추출 ──────────────────────────────────────────────────────────
_HB_LO: float = 0.7
_HB_HI: float = 4.0
_ALL_FEATURE_NAMES = ["peak_freq", "peak_power", "bandpower", "spectral_entropy", "snr"]
_N_FEATURES_DEFAULT = len(_ALL_FEATURE_NAMES)   # 5


def _bandpower(psd: np.ndarray, freqs: np.ndarray) -> float:
    mask = (freqs >= _HB_LO) & (freqs <= _HB_HI)
    if not mask.any():
        return 0.0
    y, x = psd[mask], freqs[mask]
    return float(np.trapz(y, x))


def _spectral_entropy(psd: np.ndarray) -> float:
    s = psd.sum()
    if s < 1e-12:
        return 0.0
    p = psd / s
    return float(-np.sum(p * np.log(p + 1e-12)))


def _extract_features(sig: np.ndarray, fps: float, n_features: int) -> np.ndarray:
    """
    n_features 에 맞춰 feature 벡터를 반환.
    현재 지원:
      5 → peak_freq, peak_power, bandpower, spectral_entropy, snr
      4 → snr 제외
    더 많은 경우 0 패딩 + TODO 경고.
    """
    s = _detrend(sig)
    freqs, psd = _welch(s, fps)
    mask_hb = (freqs >= _HB_LO) & (freqs <= _HB_HI)

    if mask_hb.any():
        pi = int(np.argmax(psd[mask_hb]))
        peak_freq  = float(freqs[mask_hb][pi])
        peak_power = float(psd[mask_hb][pi])
    else:
        peak_freq = peak_power = 0.0

    bp  = _bandpower(psd, freqs)
    se  = _spectral_entropy(psd)
    snr = peak_power / (float(psd.sum()) + 1e-12)

    all5 = np.array(
        [peak_freq, peak_power, bp, se, snr], dtype=np.float32
    )

    if n_features == 5:
        return all5
    if n_features == 4:
        return all5[:4]   # snr 제외
    if n_features < 5:
        return all5[:n_features]
    # n_features > 5: 0 패딩
    warnings.warn(
        f"[RPPGDetector] n_features={n_features} > {_N_FEATURES_DEFAULT}. "
        "Extra features will be zero-padded. "
        "TODO: implement additional features to match training.",
        RuntimeWarning,
        stacklevel=3,
    )
    padded = np.zeros(n_features, dtype=np.float32)
    padded[:5] = all5
    return padded


# ── 집계 ──────────────────────────────────────────────────────────────────
def _aggregate(probs: np.ndarray, strategy: str) -> float:
    if len(probs) == 0:
        return 0.5
    s = strategy.lower()
    if s == "mean":  return float(probs.mean())
    if s == "max":   return float(probs.max())
    if s == "p75":   return float(np.percentile(probs, 75))
    warnings.warn(
        f"[RPPGDetector] Unknown aggregation='{strategy}', using p75.",
        RuntimeWarning, stacklevel=2,
    )
    return float(np.percentile(probs, 75))


# ── tensor → RGB 이미지 ───────────────────────────────────────────────────
def _tensor_to_rgb(tensor: torch.Tensor, frame_idx: int) -> np.ndarray:
    """(1,3,T,H,W) → (H,W,3) uint8 RGB"""
    f = tensor[0, :, frame_idx, :, :].cpu().float().numpy()  # (3,H,W)
    f = np.transpose(f, (1, 2, 0))                            # (H,W,3)
    lo, hi = f.min(), f.max()
    if hi - lo > 1e-6:
        f = (f - lo) / (hi - lo) * 255.0
    else:
        f = np.zeros_like(f)
    return f.clip(0, 255).astype(np.uint8)


# ── 시각화 리포트 ─────────────────────────────────────────────────────────
def _build_report(
    *,
    full_signal: np.ndarray,
    freqs: np.ndarray,
    psd: np.ndarray,
    window_probs: np.ndarray,
    window_start_indices: list[int],
    window_size: int,
    T_total: int,
    frames: list[np.ndarray] | None,
    tensor: torch.Tensor,
    is_bgr: bool,
    final_prob: float,
    confidence: float,
) -> bytes:
    n_wins = len(window_probs)
    top3_ranks = np.argsort(window_probs)[::-1][:min(3, n_wins)].tolist()

    fig = plt.figure(figsize=(15, 10), constrained_layout=True)
    fig.suptitle(
        f"rPPG Deepfake Report  |  Fake Prob: {final_prob:.4f}"
        f"  |  Confidence: {confidence:.4f}",
        fontsize=13, fontweight="bold",
    )
    gs = fig.add_gridspec(3, 3)

    # ── Panel 1: time-domain ─────────────────────────────────────────
    ax_t = fig.add_subplot(gs[0, :])
    ax_t.plot(full_signal, color="steelblue", linewidth=0.8, label="rPPG")
    for t_s in window_start_indices:
        ax_t.axvline(t_s, color="gray", linewidth=0.4, alpha=0.45)
    ax_t.set_title("rPPG Signal (time domain)")
    ax_t.set_xlabel("Sample")
    ax_t.set_ylabel("Amplitude")
    ax_t.legend(fontsize=8)
    ax_t.grid(True, alpha=0.3)

    # ── Panel 2: PSD ────────────────────────────────────────────────
    ax_f = fig.add_subplot(gs[1, :])
    ax_f.semilogy(freqs, psd + 1e-12, color="darkorange", linewidth=0.9)
    ax_f.axvspan(_HB_LO, _HB_HI, alpha=0.15, color="green",
                 label=f"HR band [{_HB_LO}–{_HB_HI} Hz]")
    ax_f.set_title("Power Spectral Density")
    ax_f.set_xlabel("Frequency (Hz)")
    ax_f.set_ylabel("PSD")
    ax_f.legend(fontsize=8)
    ax_f.grid(True, alpha=0.3)

    # ── Panel 3: top-3 representative frames ────────────────────────
    for col, rank in enumerate(top3_ranks):
        ax = fig.add_subplot(gs[2, col])
        w_prob = float(window_probs[rank])
        w_conf = abs(w_prob - 0.5) * 2.0

        # 정확한 대표 프레임 인덱스 (window_start_indices 기반)
        t_start = window_start_indices[rank]
        rep_idx = min(t_start + window_size // 2, T_total - 1)

        rgb: np.ndarray | None = None
        if frames is not None and 0 <= rep_idx < len(frames):
            f = frames[rep_idx]
            if is_bgr and f.ndim == 3 and f.shape[2] == 3:
                f = f[:, :, ::-1].copy()
            rgb = f.astype(np.uint8)
        if rgb is None:
            rgb = _tensor_to_rgb(tensor, rep_idx)

        ax.imshow(rgb)
        ax.set_title(
            f"Win#{rank} frame#{rep_idx}\n"
            f"fake={w_prob:.3f}  conf={w_conf:.3f}",
            fontsize=8,
        )
        ax.axis("off")

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# ── 프로젝트 imports (순환 방지 위해 헬퍼 정의 후) ─────────────────────────
from ddp_backend.schemas.enums import ModelName                           # noqa: E402
from ddp_backend.detectors.visual.r_ppg_preprocessing import RPPGPreprocessing  # noqa: E402
from .base import BaseVideoConfig, BaseVideoDetector, VideoInferenceResult  # noqa: E402


# ════════════════════════════════════════════════════════════════════════════
@final
class RPPGDetector(BaseVideoDetector[BaseVideoConfig]):
    model_name   = ModelName.R_PPG
    preprocessing = RPPGPreprocessing

    # ──────────────────────────────────────────────────────────────────────
    # load_model
    # ──────────────────────────────────────────────────────────────────────
    @override
    def load_model(self) -> None:
        self.eff_model: torch.nn.Module | None = None
        self.xgb_model = None

        # ── EfficientPhys checkpoint 경로 ─────────────────────────────
        ckpt_path: Path | None = None
        for key in ("effphys_model_path", "model_path", "efficientphys_path"):
            v = getattr(self.config, key, None)
            if v:
                ckpt_path = Path(v)
                break

        if ckpt_path is None:
            warnings.warn(
                "[RPPGDetector] EfficientPhys checkpoint path not set in config "
                "(effphys_model_path / model_path / efficientphys_path). Disabled.",
                RuntimeWarning, stacklevel=2,
            )
            return

        if not ckpt_path.exists():
            warnings.warn(
                f"[RPPGDetector] Checkpoint not found: {ckpt_path}. Disabled.",
                RuntimeWarning, stacklevel=2,
            )
            return

        if _EfficientPhysClass is None:
            warnings.warn(
                "[RPPGDetector] EfficientPhys class unavailable. Disabled.",
                RuntimeWarning, stacklevel=2,
            )
            return

        # ── EfficientPhys 인스턴스화 (config 인자 optional) ───────────
        eff_kwargs: dict = {}
        for kw in ("img_size", "frame_depth", "in_channels"):
            v = getattr(self.config, f"effphys_{kw}", None)
            if v is not None:
                eff_kwargs[kw] = v

        try:
            eff: torch.nn.Module = (
                _EfficientPhysClass(**eff_kwargs)  # type: ignore[call-arg]
                if eff_kwargs
                else _EfficientPhysClass()         # type: ignore[call-arg]
            )
        except TypeError as exc:
            warnings.warn(
                f"[RPPGDetector] EfficientPhys() constructor error: {exc}. "
                "Try setting effphys_img_size / effphys_frame_depth / effphys_in_channels "
                "in config. Disabled.",
                RuntimeWarning, stacklevel=2,
            )
            return

        # ── state_dict 로딩 ───────────────────────────────────────────
        try:
            ckpt = torch.load(ckpt_path, map_location=self.device)
        except Exception as exc:
            warnings.warn(
                f"[RPPGDetector] torch.load failed ({ckpt_path}): {exc}. Disabled.",
                RuntimeWarning, stacklevel=2,
            )
            return

        sd = ckpt
        if isinstance(ckpt, dict):
            sd = ckpt.get("state_dict", ckpt.get("model", ckpt))

        clean_sd = {k.removeprefix("module."): v for k, v in sd.items()}

        missing, unexpected = eff.load_state_dict(clean_sd, strict=False)
        if missing:
            warnings.warn(
                f"[RPPGDetector] Missing keys in state_dict: {missing[:5]}…",
                RuntimeWarning, stacklevel=2,
            )
        if unexpected:
            warnings.warn(
                f"[RPPGDetector] Unexpected keys in state_dict: {unexpected[:5]}…",
                RuntimeWarning, stacklevel=2,
            )

        eff.to(self.device)
        eff.eval()
        self.eff_model = eff

        # ── XGBoost 경로 ─────────────────────────────────────────────
        xgb_path: Path | None = None
        for key in ("xgboost_model_path", "xgb_model_path", "xgboost_path"):
            v = getattr(self.config, key, None)
            if v:
                xgb_path = Path(v)
                break

        if xgb_path is None:
            warnings.warn(
                "[RPPGDetector] XGBoost model path not set in config "
                "(xgboost_model_path / xgb_model_path / xgboost_path). Disabled.",
                RuntimeWarning, stacklevel=2,
            )
            self.eff_model = None
            return

        xgb_model = _load_xgb(xgb_path)
        if xgb_model is None:
            self.eff_model = None
            return
        self.xgb_model = xgb_model

    # ──────────────────────────────────────────────────────────────────────
    # _analyze
    # ──────────────────────────────────────────────────────────────────────
    @override
    def _analyze(self, vid_path: str | Path) -> VideoInferenceResult:
        debug: bool = bool(getattr(self.config, "debug", False))

        if self.eff_model is None or self.xgb_model is None:
            warnings.warn(
                "[RPPGDetector] Detector disabled – returning prob=0.5.",
                RuntimeWarning, stacklevel=2,
            )
            return VideoInferenceResult(prob=0.5)

        # ── 1. 전처리 ─────────────────────────────────────────────────
        n_frames   = getattr(self.config, "rppg_n_frames", None)
        img_size   = getattr(self.config, "rppg_img_size", 128)
        prep_kwargs: dict = {"vid_path": vid_path, "img_size": img_size}
        if n_frames is not None:
            prep_kwargs["n_frames"] = n_frames

        try:
            prep_result = self.preprocessing(**prep_kwargs)()
        except Exception as exc:
            warnings.warn(
                f"[RPPGDetector] RPPGPreprocessing failed: {exc}. prob=0.5.",
                RuntimeWarning, stacklevel=2,
            )
            return VideoInferenceResult(prob=0.5)

        # ── 2. 전처리 결과 파싱 ───────────────────────────────────────
        frames: list[np.ndarray] | None = None
        fps: float = 30.0
        is_bgr: bool = False

        if isinstance(prep_result, dict):
            frames = prep_result.get("frames")
            tensor_raw: torch.Tensor = prep_result["tensor"]
            fps    = float(prep_result.get("fps",    30.0))
            is_bgr = bool(prep_result.get("is_bgr", False))
        elif isinstance(prep_result, (tuple, list)):
            if len(prep_result) == 3:
                frames, tensor_raw, fps = prep_result[0], prep_result[1], float(prep_result[2])
            elif len(prep_result) == 2:
                tensor_raw, fps = prep_result[0], float(prep_result[1])
            else:
                tensor_raw = prep_result[0]
        elif isinstance(prep_result, torch.Tensor):
            tensor_raw = prep_result
        else:
            warnings.warn(
                f"[RPPGDetector] Unexpected preprocessing output type: "
                f"{type(prep_result)}. prob=0.5.",
                RuntimeWarning, stacklevel=2,
            )
            return VideoInferenceResult(prob=0.5)

        if fps <= 0 or fps > 240:
            warnings.warn(
                f"[RPPGDetector] fps={fps} out of range; defaulting to 30.",
                RuntimeWarning, stacklevel=2,
            )
            fps = 30.0

        # ── 3. Tensor 정규화 → (1,3,T,H,W) ───────────────────────────
        try:
            tensor = _canonical_tensor(tensor_raw).to(self.device)
        except ValueError as exc:
            warnings.warn(str(exc) + " prob=0.5.", RuntimeWarning, stacklevel=2)
            return VideoInferenceResult(prob=0.5)

        _, _, T_total, H, W = tensor.shape

        # ── 4. Windowing 파라미터 ─────────────────────────────────────
        window_secs: int = int(getattr(self.config, "rppg_window_secs", 3))
        stride_secs: int = int(getattr(self.config, "rppg_stride_secs", 1))
        window_size  = max(2, int(window_secs * fps))
        stride_size  = max(1, int(stride_secs * fps))
        aggregation  = str(getattr(self.config, "rppg_aggregation", "p75"))

        # ── 5. Feature dim 검증 ───────────────────────────────────────
        n_features: int = int(
            getattr(self.config, "expected_feature_dim",
            getattr(self.config, "feature_dim", 0))
        )
        if n_features == 0:
            inferred = _xgb_n_features(self.xgb_model)
            n_features = inferred if inferred else _N_FEATURES_DEFAULT

        if n_features != _N_FEATURES_DEFAULT:
            warnings.warn(
                f"[RPPGDetector] Using n_features={n_features} "
                f"(default extractor produces {_N_FEATURES_DEFAULT}). "
                "Verify this matches training.",
                RuntimeWarning, stacklevel=2,
            )

        # ── 6. Windowed rPPG 추출 + feature 생성 ─────────────────────
        all_signals:   list[np.ndarray] = []
        all_features:  list[np.ndarray] = []
        window_start_indices: list[int] = []

        raw_starts = list(range(0, T_total - window_size + 1, stride_size))
        if not raw_starts:
            raw_starts = [0]
            window_size = T_total

        for t_s in raw_starts:
            t_e = min(t_s + window_size, T_total)
            chunk = tensor[:, :, t_s:t_e, :, :]  # (1,3,win,H,W)

            try:
                with torch.no_grad():
                    raw_out = self.eff_model(chunk)
            except Exception as exc:
                warnings.warn(
                    f"[RPPGDetector] EfficientPhys inference error "
                    f"[{t_s}:{t_e}]: {exc}. Skipping window.",
                    RuntimeWarning, stacklevel=2,
                )
                continue

            # debug: 출력 통계
            if debug:
                arr_dbg = raw_out.detach().cpu().float().numpy()
                warnings.warn(
                    f"[RPPGDetector][DEBUG] window [{t_s}:{t_e}] "
                    f"output shape={tuple(arr_dbg.shape)}  "
                    f"min={arr_dbg.min():.4f}  max={arr_dbg.max():.4f}  "
                    f"std={arr_dbg.std():.4f}",
                    UserWarning, stacklevel=2,
                )

            try:
                sig = _to_signal(raw_out)
            except ValueError as exc:
                warnings.warn(str(exc) + " Skipping window.", RuntimeWarning, stacklevel=2)
                continue

            if len(sig) < 4:
                warnings.warn(
                    f"[RPPGDetector] Signal too short ({len(sig)}) "
                    "for PSD. Skipping window.",
                    RuntimeWarning, stacklevel=2,
                )
                continue

            feat = _extract_features(sig, fps, n_features)
            all_signals.append(sig)
            all_features.append(feat)
            window_start_indices.append(t_s)

        if not all_features:
            warnings.warn(
                "[RPPGDetector] No valid windows. Returning prob=0.5.",
                RuntimeWarning, stacklevel=2,
            )
            return VideoInferenceResult(prob=0.5)

        # ── 7. XGBoost 추론 ───────────────────────────────────────────
        X = np.vstack(all_features)  # (n_windows, n_features)
        xgb_n = _xgb_n_features(self.xgb_model)
        if xgb_n is not None and xgb_n != X.shape[1]:
            warnings.warn(
                f"[RPPGDetector] Feature dim mismatch: "
                f"extractor={X.shape[1]}, model expects={xgb_n}. "
                "Returning prob=0.5.",
                RuntimeWarning, stacklevel=2,
            )
            return VideoInferenceResult(prob=0.5)

        try:
            window_probs = _xgb_predict(self.xgb_model, X)
        except RuntimeError as exc:
            warnings.warn(str(exc) + " Returning prob=0.5.", RuntimeWarning, stacklevel=2)
            return VideoInferenceResult(prob=0.5)

        final_prob = float(np.clip(_aggregate(window_probs, aggregation), 0.0, 1.0))
        confidence = abs(final_prob - 0.5) * 2.0

        # ── 8. 전체 신호 + PSD (시각화용) ────────────────────────────
        full_signal = np.concatenate(all_signals).astype(np.float32)
        vis_freqs, vis_psd = _welch(_detrend(full_signal), fps)

        # ── 9. 시각화 리포트 생성 ─────────────────────────────────────
        report_bytes = _build_report(
            full_signal=full_signal,
            freqs=vis_freqs,
            psd=vis_psd,
            window_probs=window_probs,
            window_start_indices=window_start_indices,
            window_size=window_size,
            T_total=T_total,
            frames=frames,
            tensor=tensor,
            is_bgr=is_bgr,
            final_prob=final_prob,
            confidence=confidence,
        )

        # ── 10. VideoInferenceResult 조립 ─────────────────────────────
        result = VideoInferenceResult(prob=final_prob, image=report_bytes)
        for attr in ("confidence", "meta", "extra"):
            if not hasattr(result, attr):
                continue
            existing = getattr(result, attr)
            if isinstance(existing, dict):
                existing["confidence"] = confidence
            else:
                try:
                    setattr(result, attr, confidence)
                except (AttributeError, TypeError):
                    continue
            break

        return result

# from insightface.app import FaceAnalysis  # type: ignore
# from insightface.app.common import Face  # type: ignore
# from insightface.utils.face_align import norm_crop  # type: ignore
# from pydantic import TypeAdapter
# from torchvision.transforms import v2  # type: ignore
# from wavelet_lib.config_type import WaveletConfig  # type: ignore
# from wavelet_lib.detectors import DETECTOR  # type: ignore
# from wavelet_lib.detectors.base_detector import (  # type: ignore
#     AbstractDetector,
#     PredDict,
# )

# from ddp_backend.schemas.config import WaveletConfig as WaveletConfigParam
# from ddp_backend.schemas.enums import ModelName

# from .base import (
#     BaseVideoDetector,
#     VideoInferenceResult,
# )

# # ─────────────────────────────────────────────────────────────
# # 추론 개선 상수 (inference_result.py 와 동기화)
# # ─────────────────────────────────────────────────────────────
# _MAX_FRAMES       = 64    # [H] 프레임 수 (32 → 64)
# _TEMPERATURE      = 0.3   # [A] Temperature Scaling (T<1 → 확률 분포 샤프닝)
# _TTA_ENABLED      = True  # [C] Test-Time Augmentation (flip + brightness)
# _FACE_PAD_RATIO   = 0.3   # [D] bbox fallback 패딩 비율
# _BLUR_THRESHOLD   = 100   # [G] Laplacian variance < 이 값 → 블러 프레임 제거
# _FACE_SCORE_THR   = 0.7   # [G] InsightFace det_score < 이 값 → 저신뢰 제거
# _AGGREGATION      = "p75" # [E] 집계 전략: mean / max / p75 / any_frame


# class WaveletDetector(BaseVideoDetector[WaveletConfigParam]):
#     model_name = ModelName.WAVELET

#     @classmethod
#     def from_yaml(
#         cls,
#         yaml_path: str | Path,
#         img_size: int,
#         ckpt_path: str | Path,
#         threshold: float = 0.5,
#     ) -> Self:
#         with open(yaml_path, "r") as f:
#             raw_data = yaml.safe_load(f)
#             model_config = TypeAdapter(WaveletConfig).validate_python(raw_data)

#         new_config = WaveletConfigParam(
#             model_path=ckpt_path,
#             img_size=img_size,
#             mean=model_config["mean"],
#             std=model_config["std"],
#             threshold=threshold,
#             model_name=model_config["model_name"],
#             loss_func=model_config["loss_func"],
#         )
#         return cls(new_config)

#     @override
#     def load_model(self):
#         ckpt_path = Path(self.config.model_path)

#         if not ckpt_path.exists():
#             warnings.warn(
#                 f"[WaveletDetector] checkpoint not found: {ckpt_path}. "
#                 "Wavelet detector will be disabled (server will still start)."
#             )
#             self.model = None
#             return

#         print(f"Loading on device: {self.device}...")
#         wavelet_config: WaveletConfig = {
#             "mean": self.config.mean,
#             "std": self.config.std,
#             "model_name": self.config.model_name,
#             "loss_func": self.config.loss_func,
#             "backbone_trainable_layers": 4,
#             "class_weights": [1.0, 8.0],
#         }
#         self.model: AbstractDetector = DETECTOR[self.config.model_name](
#             config=wavelet_config
#         ).to(self.device)
#         ckpt: dict[str, Any] = torch.load(
#             self.config.model_path, map_location=self.device
#         )
#         state_dict = ckpt.get("state_dict", ckpt.get("model", ckpt))
#         state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
#         _ = self.model.load_state_dict(state_dict, strict=False)
#         _ = self.model.eval()

#         providers = (
#             ["CUDAExecutionProvider", "CPUExecutionProvider"]
#             if str(self.device) != "cpu"
#             else ["CPUExecutionProvider"]
#         )

#         self.face_app: FaceAnalysis = FaceAnalysis(
#             name="buffalo_l",
#             providers=providers,
#         )
#         self.face_app.prepare(ctx_id=0, det_size=(640, 640))  # type: ignore

#         print("Load Complete.")

#     # ──────────────────────────────────────────────────────────
#     # [B] 얼굴 정렬 / 크롭 헬퍼
#     # ──────────────────────────────────────────────────────────
#     def _get_aligned_face(self, img_rgb: MatLike) -> MatLike:
#         """
#         [B] InsightFace kps 기반 정렬 우선, 실패 시 bbox 크롭 fallback.
#         img_rgb: RGB numpy array
#         """
#         faces: list[Face] = self.face_app.get(img_rgb)  # type: ignore
#         if not faces:
#             return img_rgb

#         face = max(
#             faces,
#             key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),  # type: ignore
#         )

#         # norm_crop (5-keypoint alignment)
#         if face.kps is not None:
#             try:
#                 aligned = norm_crop(
#                     img_rgb, landmark=face.kps, image_size=self.config.img_size
#                 )
#                 if aligned is not None:
#                     return aligned  # type: ignore
#             except Exception:
#                 pass

#         # Fallback: padded bbox crop
#         x1, y1, x2, y2 = map(int, face.bbox)  # type: ignore
#         h, w = img_rgb.shape[:2]
#         pw = int((x2 - x1) * _FACE_PAD_RATIO)
#         ph = int((y2 - y1) * _FACE_PAD_RATIO)
#         x1 = max(0, x1 - pw)
#         y1 = max(0, y1 - ph)
#         x2 = min(w, x2 + pw)
#         y2 = min(h, y2 + ph)
#         crop = img_rgb[y1:y2, x1:x2]
#         return crop if crop.size > 0 else img_rgb

#     # ──────────────────────────────────────────────────────────
#     # [A] Temperature Scaling 단일 추론
#     # ──────────────────────────────────────────────────────────
#     def _infer_single(
#         self,
#         img_rgb: MatLike,
#         transform: v2.Compose,
#         img_size: int,
#     ) -> float:
#         """단일 RGB 이미지 → fake prob ([A] TEMPERATURE 적용)."""
#         resized = cv2.resize(img_rgb, (img_size, img_size))
#         img_tensor = cast(torch.Tensor, transform(resized)).unsqueeze(0).to(self.device)
#         data_dict = {
#             "image": img_tensor,
#             "label": torch.zeros(1).long().to(self.device),
#         }
#         with torch.no_grad():
#             pred: PredDict = self.model(data_dict, inference=False)
#             prob = torch.softmax(pred["cls"] / _TEMPERATURE, dim=1)[:, 1].item()
#         return float(prob)

#     # ──────────────────────────────────────────────────────────
#     # 시각화 리포트 (기존 유지)
#     # ──────────────────────────────────────────────────────────
#     @staticmethod
#     def generate_visual_report(best_img_rgb: MatLike, max_prob: float):
#         gray = cv2.cvtColor(best_img_rgb, cv2.COLOR_RGB2GRAY)
#         coeffs = pywt.dwt2(gray, "haar")  # type: ignore
#         _, (LH, HL, HH) = coeffs  # type: ignore
#         energy_map = np.sqrt(LH**2 + HL**2 + HH**2)  # type: ignore
#         energy_map: np.ndarray = cv2.normalize(  # type: ignore
#             energy_map,
#             None,  # type: ignore
#             0,
#             255,
#             cv2.NORM_MINMAX,
#         ).astype(np.uint8)

#         fig, axes = plt.subplots(1, 2, figsize=(10, 5))  # type: ignore
#         axes[0].imshow(best_img_rgb)
#         axes[0].set_title(f"Target Face (Prob: {max_prob:.4f})")
#         axes[0].axis("off")

#         im = axes[1].imshow(energy_map, cmap="magma")
#         axes[1].set_title("Wavelet High-Freq Energy Map")
#         axes[1].axis("off")
#         plt.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04)  # type: ignore

#         buf = BytesIO()
#         plt.savefig(buf, format="png", bbox_inches="tight")  # type: ignore
#         plt.close(fig)
#         return buf.getvalue()

#     # ──────────────────────────────────────────────────────────
#     # 메인 추론 (inference_result.py 개선사항 통합)
#     # ──────────────────────────────────────────────────────────
#     @override
#     def _analyze(self, vid_path: str | Path) -> VideoInferenceResult:
#         img_size = self.config.img_size
#         transform = v2.Compose(
#             [
#                 v2.ToImage(),
#                 v2.ToDtype(torch.float32),
#                 v2.Normalize(mean=self.config.mean, std=self.config.std),
#             ]
#         )

#         # ── Step 1: [H] 균등 간격 프레임 샘플링 ──────────────
#         print("Starting analyze (wavelet)...")
#         raw_frames: list[MatLike] = []
#         with self._load_video(vid_path) as cap:
#             total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
#             n_sample = min(_MAX_FRAMES, max(total, 1))
#             indices = np.linspace(0, total - 1, n_sample, dtype=int)

#             for idx in indices:
#                 cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
#                 ret, frame = cap.read()
#                 if ret:
#                     raw_frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

#         if not raw_frames:
#             raise RuntimeError

#         # ── Step 2: [G] 프레임 품질 필터링 ──────────────────
#         valid_frames: list[MatLike] = []
#         for rgb in raw_frames:
#             # 블러 검사
#             gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
#             if cv2.Laplacian(gray, cv2.CV_64F).var() < _BLUR_THRESHOLD:
#                 continue
#             # 얼굴 신뢰도 검사
#             faces: list[Face] = self.face_app.get(rgb)  # type: ignore
#             if not faces:
#                 continue
#             best = max(
#                 faces,
#                 key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),  # type: ignore
#             )
#             if best.det_score < _FACE_SCORE_THR:
#                 continue
#             valid_frames.append(rgb)

#         if not valid_frames:
#             valid_frames = raw_frames  # fallback: 필터링된 게 없으면 원본 사용

#         # ── Step 3: [B]+[C] 얼굴 정렬 + TTA 추론 ────────────
#         all_probs: list[float] = []
#         max_prob: float = -1.0
#         best_face_rgb: MatLike | None = None

#         for rgb in valid_frames:
#             # [B] 얼굴 정렬 / 크롭
#             face_rgb = self._get_aligned_face(rgb)

#             # [C] TTA view 구성: 원본 + flip + brightness ×1.1 / ×0.9
#             views: list[MatLike] = [face_rgb, cv2.flip(face_rgb, 1)]
#             if _TTA_ENABLED:
#                 views.append(
#                     np.clip(face_rgb.astype(np.float32) * 1.1, 0, 255).astype(np.uint8)
#                 )
#                 views.append(
#                     np.clip(face_rgb.astype(np.float32) * 0.9, 0, 255).astype(np.uint8)
#                 )

#             # 각 view 추론 후 평균
#             frame_probs = [self._infer_single(v, transform, img_size) for v in views]
#             avg_p = float(np.mean(frame_probs))
#             all_probs.append(avg_p)

#             if avg_p > max_prob:
#                 max_prob = avg_p
#                 best_face_rgb = face_rgb

#         if not all_probs:
#             raise RuntimeError

#         # ── Step 4: [E] p75 집계 ─────────────────────────────
#         arr = np.array(all_probs)
#         if _AGGREGATION == "mean":
#             final_prob = float(np.mean(arr))
#         elif _AGGREGATION == "max":
#             final_prob = float(np.max(arr))
#         elif _AGGREGATION in ("p75", "any_frame"):
#             final_prob = float(np.percentile(arr, 75))
#         else:
#             final_prob = float(np.mean(arr))

#         # ── 시각화 리포트 ─────────────────────────────────────
#         visual_report = None
#         if best_face_rgb is not None:
#             visual_report = self.generate_visual_report(best_face_rgb, max_prob)

#         return VideoInferenceResult(prob=final_prob, image=visual_report)
