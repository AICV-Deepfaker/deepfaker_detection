from pathlib import Path
from dotenv import load_dotenv

from pydantic_settings import BaseSettings


# .env 파일의 내용을 환경 변수로 부르기 
BASE_DIR = Path(__file__).parent.parent  # ddp_backend/core/ -> ddp_backend/ -> 루트
load_dotenv(BASE_DIR / ".env") 

# JWT 토큰 생성을 위한 환경 설정
class Settings(BaseSettings):
    DATABASE_URL: str
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
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-northeast-2"
    AWS_S3_BUCKET: str = ""

    class Config:
        env_file = ".env"

settings = Settings() # type: ignore

# 환경 변수에서 URL을 가져와 DB 엔진 만들기 
DATABASE_URL = settings.DATABASE_URL
REDIS_URL = settings.REDIS_URL