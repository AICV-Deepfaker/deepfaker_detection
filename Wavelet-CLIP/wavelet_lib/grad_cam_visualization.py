import os
import yaml
import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
import pywt

# Grad-CAM 관련 라이브러리
from pytorch_grad_cam import GradCAM, HiResCAM, ScoreCAM, GradCAMPlusPlus, AblationCAM, XGradCAM, EigenCAM, FullGrad
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from pytorch_grad_cam.utils.image import show_cam_on_image

from detectors import DETECTOR
from torchvision import transforms as T
from PIL import Image
from tqdm import tqdm

# =========================
# 0. 기본 설정 및 경로
# =========================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

DETECTOR_YAML = "/content/Wavelet-CLIP/training/config/detector/detector.yaml"
CKPT_PATH = "/content/logs/training/clip_wavelet_CelebDFv2_wavelet_2026-02-02-03-32-55/test/Celeb-DF-v2/ckpt_best.pth"

# 테스트할 이미지 경로 (하나만)
IMG_PATH = "/ssd_scratch/deep_fake_dataset/Celeb-synthesis/frames/id0_id16_0000/000.png"

IMG_SIZE = 224   # training 때 resolution과 동일해야 함

TEST_LIST_TXT = "/content/Wavelet-CLIP/datasets/rgb/List_of_testing_videos.txt" # 실제 경로로 수정
DATA_ROOT = "/ssd_scratch/deep_fake_dataset/" # 가짜 경로 링크 사용 중이므로 그대로 유지
SAVE_DIR = "/content/gradcam_inference_results" # 결과물이 저장될 폴더

# 결과 저장 폴더 생성
os.makedirs(SAVE_DIR, exist_ok=True)


# 모델 로드
with open(DETECTOR_YAML, "r") as f:
    config = yaml.safe_load(f)

model = DETECTOR[config["model_name"]](config).to(device)
ckpt = torch.load(CKPT_PATH, map_location=device)
state_dict = {k.replace("module.", ""): v for k, v in ckpt.items()}
model.load_state_dict(state_dict, strict=True)
model.eval()

# 타겟 레이어 설정 (공유해주신 구조 기반)
target_layers = [model.backbone.encoder.layers[23].layer_norm1]

# =========================
# 1. 보조 함수들
# =========================

def load_image_for_model(img_path):
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
    pil_img = Image.fromarray(img)
    transform = T.Compose([
        T.ToTensor(),
        T.Normalize(mean=config["mean"], std=config["std"])
    ])
    return transform(pil_img).unsqueeze(0).to(device)

def wavelet_decompose(img_path):
    gray = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    gray = cv2.resize(gray, (IMG_SIZE, IMG_SIZE))
    LL, (LH, HL, HH) = pywt.dwt2(gray, 'haar')
    return LL, LH, HL, HH # 평평하게 반환

def get_energy_map(LH, HL, HH):
    energy_map = np.sqrt(LH**2 + HL**2 + HH**2)
    return cv2.normalize(energy_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

def get_test_image_paths(txt_path, root_path):
    image_paths = []
    with open(txt_path, "r") as f:
        for line in f:
            if line.strip():
                rel_path = line.strip().split()[-1].replace('.mp4', '').replace('/', '/frames/')
                full_path = os.path.join(root_path, rel_path, "000.png")
                if os.path.exists(full_path): image_paths.append(full_path)
    return image_paths

# =========================
# 2. 메인 분석 함수 (수정된 루프 방식 반영)
# =========================

def process_analysis(img_path, save_name):
    try:
        # 1. 데이터 준비
        rgb_orig = cv2.resize(cv2.cvtColor(cv2.imread(img_path), cv2.COLOR_BGR2RGB), (IMG_SIZE, IMG_SIZE))
        img_tensor = load_image_for_model(img_path)
        
        # 2. 추론
        with torch.no_grad():
            data_dict = {"image": img_tensor, "label": torch.zeros(1, dtype=torch.long).to(device)}
            pred = model(data_dict, inference=True)
            prob = pred["prob"].item()
            cls = pred["cls"].argmax(dim=-1).item()

        # 3. Wavelet & Energy
        _, LH, HL, HH = wavelet_decompose(img_path)
        energy_map = get_energy_map(LH, HL, HH)

        # 4. Grad-CAM 계산 (4차원 텐서 완벽 대응)
        targets = [ClassifierOutputTarget(cls)]
        grayscale_cam = None # 초기화 (UnboundLocalError 방지)
        
        try:
            with GradCAM(model=model, target_layers=target_layers) as cam:
                # 결과 생성
                raw_cam = cam(input_tensor=img_tensor, targets=targets, eigen_smooth=True, aug_smooth=True)
                
                # [해결책] 4차원(1, 1, H, W) 등 모든 불필요한 차원 제거
                # raw_cam이 어떤 형태든 알맹이(224, 224)만 남깁니다.
                grayscale_cam = np.array(raw_cam) # numpy 배열로 변환
                
                # 차원이 2보다 크면 (예: 4차원, 3차원) 2차원이 될 때까지 0번 인덱스만 추출
                while grayscale_cam.ndim > 2:
                    grayscale_cam = grayscale_cam[0]
                    
        except Exception as cam_e:
            print(f"⚠️ CAM failed for {save_name}: {cam_e}")
            # 에러 발생 시 검은색 배경 생성
            grayscale_cam = np.zeros((IMG_SIZE, IMG_SIZE))

        # 만약 try 블록 밖으로 나왔는데도 None이면 (비정상 상황 예방)
        if grayscale_cam is None:
            grayscale_cam = np.zeros((IMG_SIZE, IMG_SIZE))

        # 5. 오버레이 및 저장
        # grayscale_cam은 이제 무조건 (224, 224)입니다.
        cam_viz = show_cam_on_image(rgb_orig.astype(np.float32) / 255.0, grayscale_cam, use_rgb=True)
        # 5. 결과 시각화 저장
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        axes[0].imshow(rgb_orig); axes[0].set_title(f"Input ({'FAKE' if cls==1 else 'REAL'})")
        axes[1].imshow(energy_map, cmap='jet'); axes[1].set_title("Wavelet Energy")
        axes[2].imshow(cam_viz); axes[2].set_title(f"Grad-CAM (Target: {cls})")
        
        # 텍스트 정보 추가
        color = 'red' if prob > 0.5 else 'blue'
        plt.figtext(0.85, 0.5, f"Prob: {prob:.4f}\nConf: {max(prob, 1-prob)*100:.1f}%", 
                    fontsize=12, color=color, fontweight='bold', va='center')

        for ax in axes: ax.axis("off")
        
        plt.tight_layout()
        plt.savefig(os.path.join(SAVE_DIR, f"result_{save_name}.png"), dpi=100)
        plt.close(fig)

    except Exception as e:
        print(f"⚠️ Error processing {img_path}: {e}")

# =========================
# 3. 실행부
# =========================
if __name__ == "__main__":
    test_images = get_test_image_paths(TEST_LIST_TXT, DATA_ROOT)
    print(f"🚀 Found {len(test_images)} images. Starting Batch Analysis...")

    for i, path in enumerate(tqdm(test_images)):
        # 파일 식별자 생성
        file_id = "_".join(path.split('/')[-3:-1])
        process_analysis(path, f"{i:03d}_{file_id}")

    print(f"✨ Analysis Complete. Saved in {SAVE_DIR}")