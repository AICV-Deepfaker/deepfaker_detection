import os 
from dotenv import load_dotenv

from pydantic_settings import BaseSettings

# .env 파일의 내용을 환경 변수로 부르기 
load_dotenv() 

# JWT 토큰 생성을 위한 환경 설정
class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # 나중에 쓸 API 키들을 미리 등록해두기
    GROQ_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None
    NGROK_AUTH_TOKEN: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()

# 환경 변수에서 URL을 가져와 DB 엔진 만들기 
DATABASE_URL = os.getenv("DATABASE_URL")