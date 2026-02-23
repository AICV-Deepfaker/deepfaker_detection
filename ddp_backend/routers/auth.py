# routers/auth_router.py
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer #OAuth 사용
from sqlalchemy.orm import Session

from ddp_backend.core.database import get_db
from ddp_backend.schemas.user import UserLogin, TokenResponse
from ddp_backend.services.auth import login, logout, reissue_token

router = APIRouter(prefix="/auth", tags=["auth"])

# Bearer 토큰 자동 추출 (Swagger 자물쇠 버튼 생성)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# 로컬 로그인 - 이메일/비밀번호 검증 후 access/refresh 토큰 발급
@router.post("/login", response_model=TokenResponse)
def login_route(user_info: UserLogin, db: Session = Depends(get_db)):
    return login(db, user_info)

# 로컬 로그아웃 - refresh_token을 revoked=True로 변경
@router.post("/logout")
def logout_route(
    refresh_token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    return logout(db, refresh_token)

# 토큰 갱신 - refresh_token으로 access/refresh 토큰 재발급
@router.post("/reissue", response_model=TokenResponse)
def reissue_route(
    refresh_token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    return reissue_token(db, refresh_token)