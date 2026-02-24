from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, MappedAsDataclass
# config.py에서 완벽하게 세팅된 settings 객체만 가져옵니다.
from ddp_backend.core.config import settings

# DB 엔진 생성 (이제 확실하게 문자열 URL이 들어갑니다)
engine = create_engine(settings.DATABASE_URL)

# 세션(접속권) 생성 (데이터베이스와 소통)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(MappedAsDataclass, DeclarativeBase): ...

# 요청 단위로 DB 세션을 생성하고 종료하는 함수
def get_db():
    db = SessionLocal()
    try:
        yield db # API 로직(router)에 세션 전달
    finally:
        db.close()