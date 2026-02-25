from pathlib import Path
from dotenv import load_dotenv

from pydantic_settings import BaseSettings, SettingsConfigDict


# .env 파일의 내용을 환경 변수로 부르기 
BASE_DIR = Path(__file__).parent.parent  # ddp_backend/core/ -> ddp_backend/ -> 루트
load_dotenv(BASE_DIR / ".env") 

# JWT 토큰 생성을 위한 환경 설정
class Settings(BaseSettings):
    REDIS_URL: str | None = None
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    # Google 로그인 요청
    GOOGLE_AUTH_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL: str = "https://www.googleapis.com/oauth2/v3/userinfo"
    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    # Google 임시 비밀번호 메일 발송
    GMAIL_USER: str
    GMAIL_APP_PASSWORD: str
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",   # 그대로 두고 싶으면 forbid 유지
    )
    DATABASE_URL: str = "sqlite:///./test.db"
    S3_BUCKET: str | None = None
    AWS_REGION: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    # model configurations
    WAVELET_YAML_PATH: str = "Wavelet-CLIP/wavelet_lib/config/detector/detector.yaml"
    WAVELET_MODEL_PATH: str = "/home/ubuntu/deepfaker_detection/ckpt_best_5.pth"
    WAVELET_IMG_SIZE: int = 224
    UNITE_MODEL_PATH: str = "./unite_baseline.onnx"
    UNITE_IMG_SIZE: int = 384
    RPPG_MODEL_PATH: str = ""
    RPPG_IMG_SIZE: int = 0



settings = Settings() # type: ignore

# 환경 변수에서 URL을 가져와 DB 엔진 만들기 
DATABASE_URL = settings.DATABASE_URL
REDIS_URL = settings.REDIS_URL

S3_BUCKET = settings.S3_BUCKET