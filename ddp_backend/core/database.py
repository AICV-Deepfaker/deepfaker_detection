from sqlalchemy import create_engine, MetaData  # MetaData 추가
from sqlalchemy.orm import sessionmaker, DeclarativeBase, MappedAsDataclass
from core.config import DATABASE_URL

# DB 엔진 생성
engine = create_engine(DATABASE_URL)

# 세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 수정 부분 시작 ---
# 1. 공용 MetaData 객체 생성
metadata_obj = MetaData()

# 2. Base 클래스가 이 metadata_obj를 사용하도록 설정
class Base(MappedAsDataclass, DeclarativeBase):
    metadata = metadata_obj

# 3. (핵심) 실행 시마다 메모리 상의 설계도(테이블 정보)를 초기화
Base.metadata.clear()
# --- 수정 부분 끝 ---

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()