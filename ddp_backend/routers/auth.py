# routers/auth_router.py
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import SecretStr
from sqlmodel.orm.session import Session

from ddp_backend.core.config import settings
from ddp_backend.core.database import get_db
from ddp_backend.core.security import (
    create_access_token,
    create_refresh_token,
    oauth2_scheme,
)
from ddp_backend.schemas.enums import LoginMethod
from ddp_backend.schemas.user import TokenResponse, UserCreate
from ddp_backend.services.auth import login, logout, reissue_token, save_refresh_token
from ddp_backend.services.user import register

# 구글 로그인, 로그아웃, 탈퇴 진행되는지 확인

router = APIRouter(prefix="/auth", tags=["auth"])

# 구글 
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


# 로컬 로그인 - 이메일/비밀번호 검증 후 access/refresh 토큰 발급
@router.post("/login", response_model=TokenResponse)
def login_route(user_info: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    return login(db, user_info.username, SecretStr(user_info.password))

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
# app_redirect: 프론트엔드가 실행 중인 Expo 주소 (Expo Go: exp://..., 빌드: ddp://auth)
@router.get("/google")
def google_auth(app_redirect: str = "ddp://auth"):
    # app_redirect를 OAuth state에 담아 Google → callback까지 전달
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": urllib.parse.quote(app_redirect, safe=""),
    }
    query = urllib.parse.urlencode(params)
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{query}")

# Google OAuth 콜백 - 토큰 발급 후 앱 주소로 redirect
@router.get("/google/callback")
def google_callback(code: str, state: str = "ddp://auth", db: Session = Depends(get_db)):
    # state에서 프론트엔드 주소 복원
    app_redirect = urllib.parse.unquote(state)

    with httpx.Client() as client:
        token_data = client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }).json()

        if "access_token" not in token_data:
            # code 재사용 등 실패 → 앱으로 에러 전달
            error_msg = urllib.parse.quote(token_data.get("error_description", "구글 인증에 실패했습니다"), safe="")
            return RedirectResponse(f"{app_redirect}?error={error_msg}", status_code=302)

        userinfo = client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        ).json()

    # 회원가입 또는 기존 유저 조회
    user_info = UserCreate(
        email=userinfo["email"],
        name=userinfo.get("name", ""),
        password=None,
        profile_image=userinfo.get("picture"),
    )
    user = register(db, user_info, LoginMethod.GOOGLE)

    # 앱 토큰 발급
    access_token = create_access_token(user.user_id)
    refresh_token = create_refresh_token(user.user_id)
    save_refresh_token(
        db,
        user_id=user.user_id,
        refresh_token=refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )

    # 프론트엔드의 Expo 주소로 토큰 전달
    token_query = urllib.parse.urlencode({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": str(user.user_id),
        "email": user.email,
        "nickname": user.nickname or "",
    })
    return RedirectResponse(f"{app_redirect}?{token_query}", status_code=302)