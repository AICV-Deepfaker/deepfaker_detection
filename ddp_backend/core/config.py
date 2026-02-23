import os 
from pathlib import Path
from dotenv import load_dotenv

from pydantic_settings import BaseSettings

# .env 파일의 내용을 환경 변수로 부르기 
_CONFIG_DIR = Path(__file__).parent.parent  # ddp_backend/
load_dotenv(_CONFIG_DIR / ".env")

# JWT 토큰 생성을 위한 환경 설정
class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    # Google OAuth 추가
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    class Config:
        env_file = ".env"

settings = Settings()

# 환경 변수에서 URL을 가져와 DB 엔진 만들기 
DATABASE_URL = os.getenv("DATABASE_URL")