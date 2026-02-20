import os
import shutil
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Literal

import torch
import uvicorn
from detectors.base_detector import BaseDetector, BaseVideoConfig, Scorable
from detectors.stt_detector import STTDetector
from detectors.unite_detector import UniteDetector

# from core.database import engine
# from models.models import Base
from detectors.wavelet_detector import WaveletDetector

# ==========================================
# .env 로드
# ==========================================
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel
from pyngrok import ngrok
from schemas import APIOutput, BaseReport, STTReport, VideoReport

_BACKEND_DIR = Path(__file__).parent
load_dotenv(_BACKEND_DIR / ".env")

# ==========================================
# STT 파이프라인 설정
# ==========================================
_STT_DIR = Path(__file__).parent.parent / "STT"
sys.path.insert(0, str(_STT_DIR))

# STT .env도 추가 로드 (GROQ_API_KEY, TAVILY_API_KEY가 backend .env에 없을 경우 대비)
load_dotenv(_STT_DIR / ".env")

_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v"}


def _is_video(filename: str) -> bool:
    return Path(filename).suffix.lower() in _VIDEO_EXTENSIONS


# 서버가 시작될 때 테이블이 없으면 자동 생성 (JPA의 ddl-auto 같은 역할)
# Base.metadata.create_all(bind=engine)

# 모델 및 환경 변수
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DETECTOR_YAML = "Wavelet-CLIP/wavelet_lib/config/detector/detector.yaml"
CKPT_PATH = "ddp_backend/ckpt_best.pth"
IMG_SIZE = 224

NGROK_AUTH_TOKEN = os.environ.get("NGROK_AUTH_TOKEN", "")

# UniteDetector (정밀탐지모드 / deep)
unite_detector = UniteDetector(
    BaseVideoConfig(
        model_path="./unite_baseline.onnx",
        img_size=384,
    )
)

# WaveletDetector (증거수집모드 / fast)
wavelet_detector = WaveletDetector.from_yaml(DETECTOR_YAML, IMG_SIZE, CKPT_PATH)

detectors: dict[str, BaseDetector[Any, BaseReport]] = {
    "UNITE": unite_detector,
    "wavelet": wavelet_detector,
    "STT": STTDetector(),
}


@asynccontextmanager
async def lifespan(app: FastAPI):  # pyright: ignore[reportUnusedParameter]
    for next_detector in detectors.values():
        next_detector.load_model()
    public_url = None

    if NGROK_AUTH_TOKEN:
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
@app.post("/predict/{mode}")
async def predict_deepfake(
    file: Annotated[UploadFile, File(...)], mode: Literal["deep", "fast"] = "fast"
) -> APIOutput:
    temp_path = f"temp_{file.filename}"
    model_names: dict[str, list[str]] = {"deep": ["UNITE"], "fast": ["wavelet", "STT"]}
    probs: list[float] = []
    reports: dict[str, BaseReport | VideoReport | STTReport] = {}
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        for next_model in model_names[mode]:
            model = detectors[next_model]

            report = await model.analyze(temp_path)
            reports[next_model] = report
            if isinstance(report, Scorable):
                probs.append(report.prob)

        avg_prob = sum(probs) / len(probs)
        confidence = avg_prob if avg_prob > 0.5 else 1 - avg_prob
        return APIOutput(
            status="success",
            result="FAKE" if avg_prob > 0.5 else "REAL",
            average_fake_prob=round(avg_prob, 4),
            confidence_score=f"{round(confidence * 100, 2)}%",
            analysis_mode=mode,
            reports=reports,
        )
    except Exception as e:
        return APIOutput(
            status="error",
            error_msg=str(e),
            result="FAKE",
            average_fake_prob=0,
            confidence_score="",
            analysis_mode=mode,
            reports={},
        )
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
