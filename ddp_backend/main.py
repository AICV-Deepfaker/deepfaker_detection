import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import torch
import uvicorn

# from core.database import engine
# from models.models import Base
# ==========================================
# .env 로드
# ==========================================
from dotenv import load_dotenv
from fastapi import FastAPI
from pyngrok import ngrok # type: ignore

from services.dependencies import load_all_model
from routers import detection

_BACKEND_DIR = Path(__file__).parent
load_dotenv(_BACKEND_DIR / ".env")


# ==========================================
# DB 생성
# ==========================================
# 서버가 시작될 때 테이블이 없으면 자동 생성 (JPA의 ddl-auto 같은 역할)
Base.metadata.create_all(bind=engine)


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


# 모델 및 환경 변수
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

NGROK_AUTH_TOKEN = os.environ.get("NGROK_AUTH_TOKEN", "")

@asynccontextmanager
async def lifespan(app: FastAPI):  # pyright: ignore[reportUnusedParameter]
    load_all_model()
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
app.include_router(detection.router)



# ==========================================
# 6. 메인 실행부
# ==========================================
if __name__ == "__main__":
    # 일반 .py 파일에서는 nest_asyncio와 uvicorn.run 조합보다
    # uvicorn.run(app) 직접 호출이 더 안정적입니다.
    uvicorn.run(app, host="0.0.0.0", port=8000)
