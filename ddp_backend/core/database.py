from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine
from sqlmodel.orm.session import Session
from ddp_backend.core.config import DATABASE_URL

# DB 엔진 생성
engine = create_engine(DATABASE_URL)

# 세션(접속권) 생성 (데이터베이스와 소통)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session) #autocommit = 자동 저장, autoflush = 자동 변경 사항 저장

# 테이블을 만들 때 상속받을 기본 클래스
# Base = declarative_base() # JPA의 Entity
class Base(SQLModel): ...

# 요청 단위로 DB 세션을 생성하고 종료하는 함수
def get_db():
    db = SessionLocal()
    try:
        yield db # API 로직(router)에 세션 전달
    finally:
        db.close()