# routers/auth_router.py
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from ddp_backend.core.database import get_db
from ddp_backend.core.security import get_current_user
from ddp_backend.schemas.user import UserLogin, TokenResponse
from ddp_backend.services.auth import login, logout, reissue_token

router = APIRouter(prefix="/auth", tags=["auth"])

# 로그인 - 이메일/비밀번호 검증 후 access/refresh 토큰 발급
@router.post("/login", response_model=TokenResponse)
def login_route(user_info: UserLogin, db: Session = Depends(get_db)):
    return login(db, user_info)

# 로그아웃 - Header의 refresh_token을 revoked=True로 변경
@router.post("/logout")
def logout_route(authorization: str = Header(...), db: Session = Depends(get_db)):
    refresh_token = authorization.replace("Bearer ", "")
    return logout(db, refresh_token)

# 토큰 갱신 - Header의 refresh_token으로 access/refresh 토큰 재발급
@router.post("/reissue")
def reissue_route(authorization: str = Header(...), db: Session = Depends(get_db)):
    refresh_token = authorization.replace("Bearer ", "")
    return reissue_token(db, refresh_token)

# 토큰 생성은?