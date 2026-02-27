import os
import yaml
import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
import pywt
from wavelet_lib.detectors import DETECTOR
from torchvision import transforms as T
from PIL import Image
from tqdm import tqdm

# =========================
# 0. 기본 설정
# =========================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

DETECTOR_YAML = "/content/Wavelet-CLIP/training/config/detector/detector.yaml"
CKPT_PATH = "/content/logs/training/clip_wavelet_CelebDFv2_wavelet_2026-02-02-03-32-55/test/Celeb-DF-v2/ckpt_best.pth"

# 테스트할 이미지 경로 (하나만)
IMG_PATH = "/ssd_scratch/deep_fake_dataset/Celeb-synthesis/frames/id0_id16_0000/000.png"

IMG_SIZE = 224   # training 때 resolution과 동일해야 함

TEST_LIST_TXT = "/content/Wavelet-CLIP/datasets/rgb/List_of_testing_videos.txt" # 실제 경로로 수정
DATA_ROOT = "/ssd_scratch/deep_fake_dataset/" # 가짜 경로 링크 사용 중이므로 그대로 유지
SAVE_DIR = "/content/inference_results" # 결과물이 저장될 폴더

# 결과 저장 폴더 생성
os.makedirs(SAVE_DIR, exist_ok=True)

# =========================
# 1. 보조 함수 정의 (순서 중요)
# =========================

def load_image_for_model(img_path):
    img = cv2.imread(img_path)
    if img is None: raise ValueError(f"Failed: {img_path}")
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_CUBIC)
    pil_img = Image.fromarray(img)
    transform = T.Compose([
        T.ToTensor(),
        T.Normalize(mean=config["mean"], std=config["std"])
    ])
    return transform(pil_img).unsqueeze(0)

@torch.no_grad()
def inference_single_image(model, img_tensor):
    data_dict = {"image": img_tensor.to(device), "label": torch.zeros(1, dtype=torch.long).to(device)}
    pred = model(data_dict, inference=True)
    prob = pred["prob"].item()
    cls = pred["cls"].argmax(dim=-1).item()
    return prob, cls

def wavelet_decompose(img_path):
    gray = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    gray = cv2.resize(gray, (IMG_SIZE, IMG_SIZE))
    LL, (LH, HL, HH) = pywt.dwt2(gray, 'haar')
    return LL, LH, HL, HH

def get_test_image_paths(txt_path, root_path):
    image_paths = []
    with open(txt_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            video_rel_path = line.split()[-1]
            # .mp4 제거 및 /frames/ 삽입
            folder_rel_path = video_rel_path.replace('.mp4', '').replace('/', '/frames/')
            full_path = os.path.join(root_path, folder_rel_path, "000.png")
            if os.path.exists(full_path):
                image_paths.append(full_path)
    return image_paths

def process_and_save(img_path, save_name):
    try:
        img_tensor = load_image_for_model(img_path)
        prob, cls = inference_single_image(model, img_tensor)
        LL, LH, HL, HH = wavelet_decompose(img_path)

        rgb = cv2.imread(img_path)
        rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, (IMG_SIZE, IMG_SIZE))

        plt.figure(figsize=(12, 7))

        plt.subplot(2, 3, 1); plt.imshow(rgb); plt.title("Input Image"); plt.axis("off")
        plt.subplot(2, 3, 2); plt.imshow(np.abs(LH), cmap="gray"); plt.title("LH"); plt.axis("off")
        plt.subplot(2, 3, 3); plt.imshow(np.abs(HL), cmap="gray"); plt.title("HL"); plt.axis("off")
        plt.subplot(2, 3, 5); plt.imshow(np.abs(HH), cmap="gray"); plt.title("HH"); plt.axis("off")

        plt.subplot(2, 3, 6)
        color = 'red' if prob > 0.5 else 'blue'
        plt.text(
            0.05, 0.55,
            f"Fake Prob: {prob:.4f}\nClass: {'FAKE' if cls==1 else 'REAL'}",
            fontsize=14, color=color, weight='bold'
        )
        plt.axis("off")

        # ✅ 내부/외부 여백 줄이기
        plt.tight_layout(pad=0.2)

        out_path = os.path.join(SAVE_DIR, f"{save_name}.png")
        plt.savefig(out_path, dpi=150, bbox_inches="tight", pad_inches=0.0)
        plt.close()
    except Exception as e:
        print(f"Error on {img_path}: {e}")

# =========================
# 2. 메인 실행부
# =========================
if __name__ == "__main__":
    with open(DETECTOR_YAML, "r") as f:
        config = yaml.safe_load(f)

    model = DETECTOR[config["model_name"]](config).to(device)
    ckpt = torch.load(CKPT_PATH, map_location=device)
    state_dict = {k.replace("module.", ""): v for k, v in ckpt.items()}
    model.load_state_dict(state_dict, strict=True)
    model.eval()
    print("✅ Model & Config Loaded")

    all_test_images = get_test_image_paths(TEST_LIST_TXT, DATA_ROOT)
    print(f"🚀 Processing {len(all_test_images)} images...")

    for i, path in enumerate(tqdm(all_test_images)):
        # 파일명 생성: 'YouTube-real_00170_000' 형태
        file_id = "_".join(path.split('/')[-3:]).replace('.png', '')
        process_and_save(path, f"result_{i:04d}_{file_id}")

    print(f"✨ Finished! Saved in {SAVE_DIR}")