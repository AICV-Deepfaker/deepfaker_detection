# routers/user_router.py (길찾기)
# 외부(프론트)에서 접속할 수 있는 문을 만드는 곳입니다.

# 정의: @router.post("/signup")처럼 경로를 설정하고 위에서 만든 auth_service를 호출합니다.

# @router.post("/login")
# def login(user_data: UserLogin, db: Session = Depends(get_db)):
#     return auth_service.login(db, user_data)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from services.auth_service import create_user


# router = APIRouter()

# @router.post("/signup")
# def signup(user_data: UserCreate, db: Session = Depends(get_db)):
#     # 2. 여기서 실제로 사용(호출)하는 순간! 
#     # 상단의 'create_user' 글자색이 진하게 바뀝니다.
#     return create_user(db, user_data)