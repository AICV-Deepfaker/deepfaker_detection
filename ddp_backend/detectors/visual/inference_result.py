import os
import sys
import yaml
import torch
import numpy as np
import cv2
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from torchvision import transforms as T

# ==========================================
# 1. 경로 및 환경 설정
# ==========================================
repo_path = "/content/Wavelet-CLIP/training"
if repo_path not in sys.path:
    sys.path.append(repo_path)

from detectors import DETECTOR

DEVICE        = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DETECTOR_YAML = "/content/Wavelet-CLIP/training/config/detector/detector.yaml"
CKPT_PATH     = "/content/Wavelet-CLIP/checkpoints/ckpt_best.pth"

# ─────────────────────────────────────────────────────────────
# 분석할 영상 경로 설정
#   - 경로를 직접 지정하면 해당 파일을 바로 사용합니다.
#   - None 으로 두면 Colab 파일 업로드 다이얼로그가 열립니다.
# 예시:
#   VIDEO_PATH = "/content/drive/MyDrive/test_video.mp4"
#   VIDEO_PATH = "/content/sample.mp4"
VIDEO_PATH = None
# ─────────────────────────────────────────────────────────────

# 분석할 프레임 수 (영상 전체에서 균등 샘플링)
MAX_FRAMES = 32

# ==========================================
# 2. 모델 로드
# ==========================================
def load_model():
    print(f"모델 로딩 중... (Device: {DEVICE})")
    with open(DETECTOR_YAML, "r") as f:
        config = yaml.safe_load(f)

    model = DETECTOR[config["model_name"]](config).to(DEVICE)

    if not os.path.exists(CKPT_PATH):
        raise FileNotFoundError(f"체크포인트를 찾을 수 없습니다: {CKPT_PATH}")

    ckpt = torch.load(CKPT_PATH, map_location=DEVICE)
    state_dict = ckpt.get("state_dict", ckpt.get("model", ckpt))
    state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
    model.load_state_dict(state_dict, strict=True)
    model.eval()
    print(f"모델 로드 완료: {CKPT_PATH}")
    return model, config

# ==========================================
# 3. 영상 로드 및 프레임 추출
# ==========================================
def load_and_extract_frames(video_path=None, max_frames=MAX_FRAMES):
    """
    영상 파일에서 균등 간격으로 프레임을 추출합니다.

    Args:
        video_path (str | None):
            - 경로를 지정하면 해당 파일을 직접 사용합니다.
            - None 이면 Colab 업로드 다이얼로그가 열립니다.
        max_frames (int): 추출할 최대 프레임 수
    반환: (video_path, frames_bgr, frame_indices, fps, total_frames)
    """
    if video_path is not None and os.path.isfile(video_path):
        print(f"영상 경로 사용: {video_path}")
    else:
        if video_path is not None:
            print(f"[경고] 경로를 찾을 수 없습니다: {video_path}")
            print("Colab 업로드 다이얼로그로 전환합니다...")
        from google.colab import files
        print("영상 파일을 업로드하세요 (mp4, avi, mov 등)...")
        uploaded = files.upload()
        if not uploaded:
            raise ValueError("업로드된 파일이 없습니다.")
        video_path = list(uploaded.keys())[0]
        print(f"업로드 완료: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"영상을 열 수 없습니다: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps          = cap.get(cv2.CAP_PROP_FPS)
    duration_sec = total_frames / fps if fps > 0 else 0

    print(f"영상 정보: {total_frames}프레임 / {fps:.1f}FPS / {duration_sec:.1f}초")

    # 균등 간격으로 프레임 인덱스 선택
    n_sample = min(max_frames, total_frames)
    frame_indices = np.linspace(0, total_frames - 1, n_sample, dtype=int)

    frames_bgr = []
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, frame = cap.read()
        if ret:
            frames_bgr.append(frame)
        else:
            frames_bgr.append(None)

    cap.release()

    valid = [(f, i) for f, i in zip(frames_bgr, frame_indices) if f is not None]
    frames_bgr    = [v[0] for v in valid]
    frame_indices = [v[1] for v in valid]

    print(f"추출된 프레임: {len(frames_bgr)}개 (총 {total_frames}프레임에서 샘플링)")
    return video_path, frames_bgr, frame_indices, fps, total_frames

# ==========================================
# 4. 단일 프레임 추론
# ==========================================
def infer_frame(model, img_bgr, transform, img_size):
    """
    단일 BGR 프레임에 대해 추론을 수행합니다.
    반환: (cls_feat, hh_feat, fake_prob)
    """
    hh_feat_buf = []

    def hh_hook(module, inp, out):
        hh_feat_buf.append(out.detach().squeeze(0).cpu().numpy())

    hook = model.img_freq_cnn.register_forward_hook(hh_hook)

    img_rgb     = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img_rgb, (img_size, img_size))
    tensor      = transform(img_resized).unsqueeze(0).to(DEVICE)
    data        = {"image": tensor, "label": torch.tensor([0]).to(DEVICE)}

    with torch.no_grad():
        cls_feat, _ = model.features(data)
        out         = model(data, inference=False)
        prob        = torch.softmax(out["cls"], dim=1)[:, 1].item()

    hook.remove()

    cls_np = cls_feat.squeeze(0).cpu().numpy()
    hh_np  = hh_feat_buf[0] if hh_feat_buf else np.zeros(256)
    return cls_np, hh_np, prob

# ==========================================
# 5. HH 서브밴드 시각화용 추출
# ==========================================
def get_hh_subband(model, img_bgr, transform, img_size):
    """
    이미지에서 HH 서브밴드(고주파 성분)를 추출하여 시각화용 numpy 배열로 반환합니다.
    """
    img_rgb     = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img_rgb, (img_size, img_size))
    tensor      = transform(img_resized).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        _, yh_img = model.dwt2d(tensor)
        hh        = yh_img[0][:, :, 2, :, :]   # (1, 3, H', W')
        hh        = hh.squeeze(0).cpu().numpy()  # (3, H', W')

    # 시각화를 위해 절댓값 취하고 정규화
    hh_vis = np.abs(hh).transpose(1, 2, 0)   # (H', W', 3)
    hh_vis = (hh_vis - hh_vis.min()) / (hh_vis.max() - hh_vis.min() + 1e-8)
    return hh_vis

# ==========================================
# 6. 전체 프레임 추론
# ==========================================
def run_inference(model, config, frames_bgr, frame_indices, fps):
    img_size  = config.get("resolution", 224)
    mean      = config.get("mean", [0.5, 0.5, 0.5])
    std       = config.get("std",  [0.5, 0.5, 0.5])
    transform = T.Compose([T.ToTensor(), T.Normalize(mean=mean, std=std)])

    cls_feats, hh_feats, probs, timestamps = [], [], [], []

    print(f"\n추론 중... ({len(frames_bgr)}프레임)")
    for frame, idx in zip(frames_bgr, frame_indices):
        cls_np, hh_np, prob = infer_frame(model, frame, transform, img_size)
        cls_feats.append(cls_np)
        hh_feats.append(hh_np)
        probs.append(prob)
        timestamps.append(idx / fps if fps > 0 else idx)

    return np.array(cls_feats), np.array(hh_feats), np.array(probs), np.array(timestamps)

# ==========================================
# 7. 대표 프레임 선택 (가장 Fake/Real 확신 프레임)
# ==========================================
def select_representative_frames(frames_bgr, probs, n=4):
    """
    Fake 확률이 가장 높은 n개 + 가장 낮은 n개 프레임을 반환합니다.
    """
    sorted_idx = np.argsort(probs)
    real_idx   = sorted_idx[:n]          # 가장 Real에 가까운 프레임
    fake_idx   = sorted_idx[-n:][::-1]   # 가장 Fake에 가까운 프레임
    return real_idx, fake_idx

# ==========================================
# 8. 시각화
# ==========================================
def visualize(video_path, frames_bgr, probs, timestamps,
              cls_feats, model, config):
    avg_prob    = float(np.mean(probs))
    verdict     = "FAKE" if avg_prob >= 0.5 else "REAL"
    verdict_col = "#e74c3c" if verdict == "FAKE" else "#2ecc71"
    img_size    = config.get("resolution", 224)
    mean        = config.get("mean", [0.5, 0.5, 0.5])
    std         = config.get("std",  [0.5, 0.5, 0.5])
    transform   = T.Compose([T.ToTensor(), T.Normalize(mean=mean, std=std)])

    n_frames    = len(frames_bgr)
    real_idx, fake_idx = select_representative_frames(frames_bgr, probs, n=4)

    # ── Figure 레이아웃 ─────────────────────────────────────────────
    # Row 0 (colspan 2): 최종 판정 배너
    # Row 1 (colspan 2): 프레임별 확률 타임라인
    # Row 2 (colspan 2): 확률 분포 히스토그램
    # Row 3: Real로 분류된 대표 프레임 4개
    # Row 4: Fake로 분류된 대표 프레임 4개
    # Row 5: HH 고주파 서브밴드 시각화 (Fake 대표 4개)
    fig = plt.figure(figsize=(22, 30))
    video_name = os.path.basename(video_path)
    fig.suptitle(
        f"Inference Result — {video_name}\n"
        f"Overall Verdict: [{verdict}]  (Fake Prob = {avg_prob:.4f})",
        fontsize=18, fontweight='bold', y=0.99,
        color=verdict_col
    )
    gs = gridspec.GridSpec(6, 4, figure=fig,
                           hspace=0.5, wspace=0.3,
                           top=0.95, bottom=0.02)

    # ── Row 0: 판정 배너 ──────────────────────────────────────────
    ax_banner = fig.add_subplot(gs[0, :])
    ax_banner.set_facecolor(verdict_col)
    ax_banner.text(
        0.5, 0.5,
        f"VERDICT: {verdict}  |  Avg Fake Probability: {avg_prob:.4f}  "
        f"|  Frames Analyzed: {n_frames}",
        transform=ax_banner.transAxes,
        fontsize=16, fontweight='bold', color='white',
        va='center', ha='center'
    )
    ax_banner.axis('off')

    # ── Row 1: 타임라인 ──────────────────────────────────────────
    ax_time = fig.add_subplot(gs[1, :])
    ax_time.plot(timestamps, probs, color='steelblue', lw=2, marker='o',
                 markersize=4, label='Fake Probability')
    ax_time.axhline(0.5, color='red', linestyle='--', lw=1.5, label='Threshold (0.5)')
    ax_time.fill_between(timestamps, probs, 0.5,
                         where=(np.array(probs) >= 0.5),
                         alpha=0.25, color='red',   label='Fake region')
    ax_time.fill_between(timestamps, probs, 0.5,
                         where=(np.array(probs) <  0.5),
                         alpha=0.25, color='green', label='Real region')
    ax_time.set_xlim(timestamps[0], timestamps[-1])
    ax_time.set_ylim(0, 1)
    ax_time.set_xlabel("Time (seconds)", fontsize=11)
    ax_time.set_ylabel("Fake Probability", fontsize=11)
    ax_time.set_title("Frame-by-Frame Fake Probability Timeline", fontsize=13)
    ax_time.legend(fontsize=9, loc='upper right')
    ax_time.grid(alpha=0.3)

    # ── Row 2: 히스토그램 ──────────────────────────────────────────
    ax_hist = fig.add_subplot(gs[2, :])
    ax_hist.hist(probs, bins=20, range=(0, 1), color='steelblue',
                 alpha=0.7, edgecolor='white')
    ax_hist.axvline(0.5, color='red', linestyle='--', lw=2, label='Threshold')
    ax_hist.axvline(avg_prob, color='orange', linestyle='-', lw=2,
                    label=f'Mean = {avg_prob:.4f}')
    ax_hist.set_xlabel("Fake Probability", fontsize=11)
    ax_hist.set_ylabel("Frame Count", fontsize=11)
    ax_hist.set_title("Distribution of Frame Probabilities", fontsize=13)
    ax_hist.legend(fontsize=9)
    ax_hist.grid(alpha=0.3)

    # ── Row 3: Real로 분류된 대표 프레임 ─────────────────────────
    for col, idx in enumerate(real_idx):
        ax = fig.add_subplot(gs[3, col])
        img_rgb = cv2.cvtColor(frames_bgr[idx], cv2.COLOR_BGR2RGB)
        ax.imshow(img_rgb)
        ax.set_title(f"Real  p={probs[idx]:.3f}\n@{timestamps[idx]:.1f}s",
                     fontsize=9, color='#27ae60')
        ax.axis('off')

    # ── Row 4: Fake로 분류된 대표 프레임 ─────────────────────────
    for col, idx in enumerate(fake_idx):
        ax = fig.add_subplot(gs[4, col])
        img_rgb = cv2.cvtColor(frames_bgr[idx], cv2.COLOR_BGR2RGB)
        ax.imshow(img_rgb)
        ax.set_title(f"Fake  p={probs[idx]:.3f}\n@{timestamps[idx]:.1f}s",
                     fontsize=9, color='#c0392b')
        ax.axis('off')

    # ── Row 5: HH 고주파 서브밴드 (Fake 대표 프레임) ─────────────
    for col, idx in enumerate(fake_idx):
        ax = fig.add_subplot(gs[5, col])
        hh_vis = get_hh_subband(model, frames_bgr[idx], transform, img_size)
        ax.imshow(hh_vis)
        ax.set_title(f"HH Subband\n@{timestamps[idx]:.1f}s",
                     fontsize=9, color='#8e44ad')
        ax.axis('off')

    save_name = f"inference_{os.path.splitext(video_name)[0]}.png"
    plt.savefig(save_name, dpi=120, bbox_inches='tight')
    plt.show()
    print(f"\n결과 저장 완료: {save_name}")

    return avg_prob, verdict

# ==========================================
# 9. 최종 결과 출력
# ==========================================
def print_verdict(video_path, probs, avg_prob, verdict):
    n_fake = int((np.array(probs) >= 0.5).sum())
    n_real = len(probs) - n_fake

    print("\n" + "="*50)
    print(f"  추론 결과: {os.path.basename(video_path)}")
    print("="*50)
    print(f"  분석 프레임  : {len(probs)}개")
    print(f"  Fake 프레임  : {n_fake}개 ({100*n_fake/len(probs):.1f}%)")
    print(f"  Real 프레임  : {n_real}개 ({100*n_real/len(probs):.1f}%)")
    print(f"  평균 Fake 확률: {avg_prob:.4f}")
    print("-"*50)
    print(f"  최종 판정     : {'[FAKE]' if verdict == 'FAKE' else '[REAL]'}")
    print("="*50)

# ==========================================
# 10. 실행
# ==========================================
if __name__ == "__main__":
    model, config = load_model()
    if hasattr(model, 'prob'):  model.prob  = []
    if hasattr(model, 'label'): model.label = []

    # 영상 로드 및 프레임 추출 (VIDEO_PATH 미설정 시 업로드 다이얼로그)
    video_path, frames_bgr, frame_indices, fps, total_frames = \
        load_and_extract_frames(video_path=VIDEO_PATH, max_frames=MAX_FRAMES)

    # 프레임별 추론
    cls_feats, hh_feats, probs, timestamps = \
        run_inference(model, config, frames_bgr, frame_indices, fps)

    # 시각화
    avg_prob, verdict = visualize(
        video_path, frames_bgr, probs, timestamps, cls_feats, model, config
    )

    # 최종 판정 출력
    print_verdict(video_path, probs, avg_prob, verdict)
