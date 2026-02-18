from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# DB 접속 정보 (유저:비밀번호@호스트:포트/DB이름)
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:1234@localhost:5432/postgres"

# DB 엔진 생성
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 세션(접속권) 생성 (데이터베이스와 소통)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) #autocommit = 자동 저장, autoflush = 자동 변경 사항 저장

# 테이블을 만들 때 상속받을 기본 클래스
Base = declarative_base() # JPA의 Entity