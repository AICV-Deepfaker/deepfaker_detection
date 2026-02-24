import os 
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from pydantic_settings import BaseSettings, SettingsConfigDict


# .env 파일의 내용을 환경 변수로 부르기 
BASE_DIR = Path(__file__).parent.parent  # ddp_backend/core/ -> ddp_backend/ -> 루트
load_dotenv(BASE_DIR / ".env") 

S3_BUCKET = os.getenv("S3_BUCKET")
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
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    #class Config:
    #  env_file = ".env"
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

settings = Settings()

# 환경 변수에서 URL을 가져와 DB 엔진 만들기 
DATABASE_URL = os.getenv("DATABASE_URL")