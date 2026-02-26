import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import torch
import uvicorn

from ddp_backend.core.database import engine
from ddp_backend.models.models import Base
from ddp_backend.core.scheduler import start_schedular, shutdown_schedular

# ==========================================
# .env 로드
# ==========================================
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pyngrok import ngrok  # type: ignore

from ddp_backend.core.redis_bridge import redis_connector
from ddp_backend.core.tk_broker import broker
from ddp_backend.routers import auth, detection, user, video, websocket

_BACKEND_DIR = Path(__file__).parent
load_dotenv(_BACKEND_DIR / ".env")

try:
    from ddp_backend.core.model import load_all_model
except Exception:
    load_all_model = None

# ==========================================
# DB 생성
# ==========================================
Base.metadata.create_all(bind=engine)


# ==========================================
# STT 파이프라인 설정
# ==========================================
_STT_DIR = Path(__file__).parent.parent / "STT"
sys.path.insert(0, str(_STT_DIR))

load_dotenv(_STT_DIR / ".env")

_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v"}


def _is_video(filename: str) -> bool:
    return Path(filename).suffix.lower() in _VIDEO_EXTENSIONS


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

NGROK_AUTH_TOKEN = os.environ.get("NGROK_AUTH_TOKEN", "")


@asynccontextmanager
async def lifespan(app: FastAPI):  # pyright: ignore[reportUnusedParameter]
    is_worker = broker.is_worker_process
    public_url = None
    task = None

    if not is_worker:
        # ── FastAPI 서버 전용 초기화 (Taskiq 워커에서는 실행 안 함) ──
        if load_all_model:
            load_all_model()
        else:
            print("[STARTUP] load_all_model() skipped (not available)")

        start_schedular()

        await broker.startup()

        loop = asyncio.get_event_loop()
        task = loop.create_task(redis_connector(app))

        if NGROK_AUTH_TOKEN:
            ngrok.set_auth_token(NGROK_AUTH_TOKEN)
            try:
                for t in ngrok.get_tunnels():
                    ngrok.disconnect(t.public_url)
            except Exception:
                pass
            try:
                ngrok.kill()
            except Exception:
                pass
            tunnel = ngrok.connect("8000")
            public_url = tunnel.public_url
            print(f"\n🚀 외부 접속 주소 (ngrok): {public_url}")
        else:
            print("\n⚠️ NGROK 토큰이 설정되지 않았습니다. 로컬에서만 접속 가능합니다.")

        print("🚀 FastAPI 서버를 시작합니다 (Port: 8000)...")

    yield

    if not is_worker:
        if task:
            task.cancel()
        shutdown_schedular()
        await broker.shutdown()
        if public_url:
            print("\n🛠️ ngrok 터널을 종료 중입니다...")
            ngrok.disconnect(public_url)
            ngrok.kill()
            print("✅ ngrok이 종료되었습니다.")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"ok": True}


# CORS 설정 - 프론트엔드(Expo) 접속 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(detection.router)
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(video.router)
app.include_router(websocket.router)


# ==========================================
# 6. 메인 실행부
# ==========================================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
