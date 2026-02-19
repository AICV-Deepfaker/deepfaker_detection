from contextlib import asynccontextmanager
import os
import shutil
from typing import Annotated

import torch
import uvicorn
from fastapi import FastAPI, File, UploadFile
from pyngrok import ngrok

# from core.database import engine
# from models.models import Base

from detectors.wavelet_detector import WaveletDetector
from detectors.unite_detector import UniteDetector
from detectors.base_detector import Config, ImageConfig

# 서버가 시작될 때 테이블이 없으면 자동 생성 (JPA의 ddl-auto 같은 역할)
# Base.metadata.create_all(bind=engine)

# 모델 및 환경 변수
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DETECTOR_YAML = "/Users/sienna/deepfaker_detection/Wavelet-CLIP/wavelet_lib/config/detector/detector.yaml"
CKPT_PATH = "/Users/sienna/deepfaker_detection/ddp_backend/ckpt_best.pth"
IMG_SIZE = 224

# ⚠️ NGROK 토큰 설정 (직접 입력하거나 환경변수 사용)
# 코랩 userdata 대신 직접 문자열로 넣거나 환경변수에서 가져오도록 수정
NGROK_AUTH_TOKEN = os.environ.get(
    "NGROK_AUTH_TOKEN", "여기에_본인의_NGROK_토큰을_입력하세요"
)

# detector = WaveletDetector.from_yaml(DETECTOR_YAML, IMG_SIZE, CKPT_PATH)
detector = UniteDetector(Config(
    model_path="./unite_baseline.onnx",
    img_config=ImageConfig(img_size=384)
))

@asynccontextmanager
async def lifespan(app: FastAPI):  # pyright: ignore[reportUnusedParameter]
    detector.load_model()
    public_url = None

    if NGROK_AUTH_TOKEN and NGROK_AUTH_TOKEN != "여기에_본인의_NGROK_토큰을_입력하세요":
        ngrok.set_auth_token(NGROK_AUTH_TOKEN)
        tunnel = ngrok.connect("8000")
        public_url = tunnel.public_url
        print(f"\n🚀 외부 접속 주소 (ngrok): {public_url}/predict")
    else:
        print("\n⚠️ NGROK 토큰이 설정되지 않았습니다. 로컬에서만 접속 가능합니다.")

    print("🚀 FastAPI 서버를 시작합니다 (Port: 8000)...")

    yield
    
    # [Shutdown] 서버 종료 시 실행
    if public_url:
        print("\n🛠️ ngrok 터널을 종료 중입니다...")
        ngrok.disconnect(public_url)
        ngrok.kill()
        print("✅ ngrok이 종료되었습니다.")

app = FastAPI(lifespan=lifespan)




# ==========================================
# API 경로
# ==========================================
@app.post("/predict")
async def predict_deepfake(file: Annotated[UploadFile, File(...)], mode: str = "full"):
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        avg_prob, visual_report = detector.analyze(temp_path)

        res = "FAKE" if avg_prob > 0.5 else "REAL"
        confidence = avg_prob if avg_prob > 0.5 else 1 - avg_prob

        return {
            "status": "success",
            "result": res,
            "average_fake_prob": round(avg_prob, 4),
            "confidence_score": f"{round(confidence * 100, 2)}%",
            "visual_report": visual_report,
            "analysis_mode": mode,
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
    # 일반 .py 파일에서는 nest_asyncio와 uvicorn.run 조합보다
    # uvicorn.run(app) 직접 호출이 더 안정적입니다.
    uvicorn.run(app, host="0.0.0.0", port=8000)