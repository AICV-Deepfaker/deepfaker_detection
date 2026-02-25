from sqlmodel import SQLModel, create_engine
from sqlmodel.orm.session import Session
from ddp_backend.core.config import settings

# DB 엔진 생성 (이제 확실하게 문자열 URL이 들어갑니다)
engine = create_engine(settings.DATABASE_URL)


# 테이블을 만들 때 상속받을 기본 클래스
# Base = declarative_base() # JPA의 Entity
class Base(SQLModel): ...

# 요청 단위로 DB 세션을 생성하고 종료하는 함수
def get_db():
    with Session(engine, autocommit=False, autoflush=False) as session:
        yield session