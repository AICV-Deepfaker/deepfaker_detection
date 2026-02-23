# routers/auth_router.py
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import httpx

from ddp_backend.core.config import settings
from ddp_backend.core.database import get_db
from ddp_backend.core.security import create_access_token, create_refresh_token, oauth2_scheme
from ddp_backend.schemas.user import UserLogin, TokenResponse, UserCreate
from ddp_backend.schemas.enums import LoginMethod
from ddp_backend.services.auth import login, logout, reissue_token, save_refresh_token
from ddp_backend.services.user import register

router = APIRouter(prefix="/auth", tags=["auth"])

# 구글 
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


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

# Google OAuth 시작
@router.get("/google")
def google_auth():
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{query}")

# Google OAuth 콜백
@router.get("/google/callback", response_model=TokenResponse)
def google_callback(code: str, db: Session = Depends(get_db)):
    with httpx.Client() as client:
        token_data = client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }).json()

        userinfo = client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        ).json()

    # 회원가입 또는 기존 유저 조회
    user_info = UserCreate(
        email=userinfo["email"],
        name=userinfo.get("name", ""),
        password=None, # google이 None이 들어올 수 있음 (service에서 처리)
        profile_image=userinfo.get("picture"),
    )
    user = register(db, user_info, LoginMethod.GOOGLE)

    # 토큰 발급
    access_token = create_access_token(user.user_id)
    refresh_token = create_refresh_token(user.user_id)
    save_refresh_token(
        db,
        user_id=user.user_id,
        refresh_token=refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.user_id,
        email=user.email,
        nickname=user.nickname
    )