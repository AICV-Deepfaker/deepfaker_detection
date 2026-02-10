import os
import yaml
import cv2
import torch
import numpy as np
import pywt
import sys
import shutil
import nest_asyncio
import uvicorn
import asyncio
import base64
import matplotlib.pyplot as plt
from io import BytesIO
from fastapi import FastAPI, UploadFile, File
from pyngrok import ngrok
from torchvision import transforms as T
from insightface.app import FaceAnalysis

# ==========================================
# 1. 경로 및 설정 (본인 환경에 맞게 수정)
# ==========================================
# Wavelet-CLIP 소스 코드가 위치한 경로
REPO_PATH = "./Wavelet-CLIP/training" 
if REPO_PATH not in sys.path:
    sys.path.append(REPO_PATH)

try:
    from detectors import DETECTOR
except ImportError:
    print("❌ 'detectors' 모듈을 찾을 수 없습니다. REPO_PATH 설정을 확인하세요.")
    sys.exit(1)

# 모델 및 환경 변수
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DETECTOR_YAML = "./Wavelet-CLIP/training/config/detector/detector.yaml"
CKPT_PATH = "./ckpt_best.pth"
IMG_SIZE = 224

# ⚠️ NGROK 토큰 설정 (직접 입력하거나 환경변수 사용)
# 코랩 userdata 대신 직접 문자열로 넣거나 환경변수에서 가져오도록 수정
NGROK_AUTH_TOKEN = os.environ.get("NGROK_AUTH_TOKEN", "여기에_본인의_NGROK_토큰을_입력하세요")

app = FastAPI()

# ==========================================
# 2. 전처리 및 시각화 유틸리티
# ==========================================
def apply_ycbcr_preprocess(img_rgb):
    img_ycrp = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2YCrCb)
    img_ycrp[:, :, 0] = 0
    return img_ycrp

def generate_visual_report(best_img_rgb, max_prob):
    gray = cv2.cvtColor(best_img_rgb, cv2.COLOR_RGB2GRAY)
    coeffs = pywt.dwt2(gray, 'haar')
    _, (LH, HL, HH) = coeffs
    energy_map = np.sqrt(LH**2 + HL**2 + HH**2)
    energy_map = cv2.normalize(energy_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    axes[0].imshow(best_img_rgb)
    axes[0].set_title(f"Target Face (Prob: {max_prob:.4f})")
    axes[0].axis('off')

    im = axes[1].imshow(energy_map, cmap='magma')
    axes[1].set_title("Wavelet High-Freq Energy Map")
    axes[1].axis('off')
    plt.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04)

    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

# ==========================================
# 3. 모델 초기화 함수
# ==========================================
def init_models():
    print(f"🔄 도구 로딩 중... (Device: {DEVICE})")
    
    if not os.path.exists(DETECTOR_YAML) or not os.path.exists(CKPT_PATH):
        print("❌ 설정 파일이나 가중치 파일(.pth)이 경로에 없습니다.")
        sys.exit(1)

    with open(DETECTOR_YAML, "r") as f:
        config = yaml.safe_load(f)
    
    model = DETECTOR[config["model_name"]](config).to(DEVICE)
    ckpt = torch.load(CKPT_PATH, map_location=DEVICE)
    state_dict = {k.replace("module.", ""): v for k, v in ckpt.items()}
    model.load_state_dict(state_dict, strict=True)
    model.eval()

    # InsightFace 로드
    face_app = FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    face_app.prepare(ctx_id=0, det_size=(640, 640))
    
    print("✅ 모델 및 얼굴 검출기 로드 완료!")
    return model, config, face_app

# 전역 변수로 할당 (서버 시작 시 로드)
model, config, face_app = init_models()

# ==========================================
# 4. 분석 엔진
# ==========================================
def process_video_analysis_full(video_path):
    cap = cv2.VideoCapture(video_path)
    all_probs = []
    max_prob = -1.0
    best_img_for_viz = None
    
    transform = T.Compose([
        T.ToTensor(),
        T.Normalize(mean=config["mean"], std=config["std"])
    ])

    print("🎬 분석 시작: 전수 조사 중...")
    
    while True:
        ret, frame = cap.read()
        if not ret: break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = face_app.get(rgb)
        
        if len(faces) > 0:
            face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
            x1, y1, x2, y2 = map(int, face.bbox)
            h, w, _ = rgb.shape
            x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
            face_crop = rgb[y1:y2, x1:x2]
        else:
            face_crop = rgb

        resized = cv2.resize(face_crop, (IMG_SIZE, IMG_SIZE))
        processed_img = apply_ycbcr_preprocess(resized)

        img_tensor = transform(processed_img).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            data_dict = {"image": img_tensor, "label": torch.zeros(1).long().to(DEVICE)}
            pred = model(data_dict, inference=True)
            prob = pred["prob"].item()
            all_probs.append(prob)

            if prob > max_prob:
                max_prob = prob
                best_img_for_viz = resized 

    cap.release()
    avg_prob = np.mean(all_probs) if all_probs else 0.0
    
    visual_report = None
    if best_img_for_viz is not None:
        visual_report = generate_visual_report(best_img_for_viz, max_prob)
        
    return float(avg_prob), visual_report

# ==========================================
# 5. API 경로
# ==========================================
@app.post("/predict")
async def predict_deepfake(file: UploadFile = File(...), mode: str = "full"):
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        avg_prob, visual_report = process_video_analysis_full(temp_path)
        
        res = "FAKE" if avg_prob > 0.5 else "REAL"
        confidence = avg_prob if avg_prob > 0.5 else 1 - avg_prob

        return {
            "status": "success",
            "result": res,
            "average_fake_prob": round(avg_prob, 4),
            "confidence_score": f"{round(confidence * 100, 2)}%",
            "visual_report": visual_report,
            "analysis_mode": mode
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ==========================================
# 6. 메인 실행부
# ==========================================
if __name__ == "__main__":
    # ngrok 설정
    if NGROK_AUTH_TOKEN and NGROK_AUTH_TOKEN != "여기에_본인의_NGROK_토큰을_입력하세요":
        ngrok.set_auth_token(NGROK_AUTH_TOKEN)
        public_url = ngrok.connect(8000)
        print(f"\n🚀 외부 접속 주소 (ngrok): {public_url}/predict")
    else:
        print("\n⚠️ NGROK 토큰이 설정되지 않았습니다. 로컬에서만 접속 가능합니다.")

    print("🚀 FastAPI 서버를 시작합니다 (Port: 8000)...")
    
    # 일반 .py 파일에서는 nest_asyncio와 uvicorn.run 조합보다 
    # uvicorn.run(app) 직접 호출이 더 안정적입니다.
    uvicorn.run(app, host="0.0.0.0", port=8000)