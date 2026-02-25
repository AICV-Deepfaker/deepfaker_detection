# services/auth.py (비즈니스 로직)
# 토큰 생성, 토큰 갱신, 비밀번호 검증, 로그인, 로그아웃


from sqlmodel.orm.session import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from ddp_backend.core.config import settings
from ddp_backend.core.security import hash_refresh_token, create_access_token, create_refresh_token, decode_token, verify_password

from ddp_backend.schemas.user import UserLogin, TokenResponse, UserCreate
from ddp_backend.schemas.enums import LoginMethod
from ddp_backend.services.crud.user import CRUDUser
from ddp_backend.services.crud.token import CRUDToken
from ddp_backend.services.user import register

import httpx

# =========
# 생성된 토큰 저장
# =========
def save_refresh_token(
        db: Session, 
        user_id: UUID, 
        refresh_token: str, 
        expires_at: datetime
        ) -> None:
    hashed = hash_refresh_token(refresh_token) # 리프레시 토큰 해시
    CRUDToken.upsert_token(db, user_id, hashed, expires_at)

# =========
# 토큰 갱신
# =========
def reissue_token(db: Session, refresh_token: str):
    # 1. DB 조회 전
    # JWT 검증
    payload = decode_token(refresh_token)
    
    user_id_str = payload.get("user_id")
    if user_id_str is None:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")

    # resfresh 토큰 타입이 아닐 때
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="refresh 토큰이 아닙니다")
    
    # payload user_id -> UUID 변환
    try:
        user_id = UUID(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
    
    # 2. DB 조회
    hashed = hash_refresh_token(refresh_token) # 리프레시 토큰 해시
    token = CRUDToken.get_by_refresh(db, hashed) # a row from token table

    # refresh 토큰이 없을 때
    if not token:
        raise HTTPException(
            status_code=401, detail="유효하지 않은 토큰입니다"
            )
    
    # payload의 user_id와 token의 user_id와 일치하지 않을경우
    if user_id != token.user_id:
        CRUDToken.set_revoked(db, hashed) # 즉시 revoked=true
        raise HTTPException(
            status_code=401, detail="사용자 정보가 일치하지 않습니다"
            )
    
    # revoked = True 시
    if token.revoked:
        raise HTTPException(
            status_code=401,
            detail="이미 로그아웃된 토큰입니다. 다시 로그인해주세요"
        )
    
    # refresh 유효
    if datetime.now(ZoneInfo("Asia/Seoul")) < token.expires_at:
        new_access_token = create_access_token(token.user_id) 
        new_refresh_token = create_refresh_token(token.user_id) 
        save_refresh_token(
            db,
            user_id=token.user_id,
            refresh_token=new_refresh_token,
            expires_at=datetime.now(ZoneInfo("Asia/Seoul")) + 
                timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        return {"access_token": new_access_token, "refresh_token": new_refresh_token}

    # 토큰 만료되었을 때 (refresh 토큰 30일 경과)
    raise HTTPException(
            status_code=401, 
            detail="세션이 만료되었습니다. 다시 로그인해주세요"
            )    

# =========
# 로컬 로그인
# =========
def login(db:Session, user_info: UserLogin) -> TokenResponse:
    # 1. 유저 조회 + 비밀번호 확인
    user = CRUDUser.get_by_email(db, user_info.email)
    if not user or user.hashed_password is None: # 유저가 없거나 패스워드(구글일 경우)가 없을 떄
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")
    if not verify_password(user_info.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="이메일 또는 비밀번호가 올바르지 않습니다"
            )

    # 2. 토큰 발급
    assert user.user_id is not None
    access_token = create_access_token(user.user_id)
    refresh_token = create_refresh_token(user.user_id)

    # 3. refresh_token 해시 후 저장
    save_refresh_token(
        db,
        user_id=user.user_id,
        refresh_token=refresh_token,
        expires_at=datetime.now(ZoneInfo("Asia/Seoul")) + 
            timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.user_id,
        email=user.email,
        nickname=user.nickname
    )


# =========
# 구글 로그인
# =========
# 1. 구글에 로그인 요청
def get_google_auth_url() -> str:
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{settings.GOOGLE_AUTH_URL}?{query}"

# 2. 구글 유저 정보 받기
def get_google_userinfo(code: str) -> UserCreate:
    with httpx.Client() as client:
        token_data = client.post(settings.GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }).json()

        if "access_token" not in token_data:
            raise HTTPException(status_code=400, detail="구글 인증에 실패했습니다")

        userinfo = client.get(
            settings.GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        ).json()

    return UserCreate(
        email=userinfo["email"],
        name=userinfo.get("name", ""),
        password=None,
        profile_image=userinfo.get("picture"),
    )

# 3. 구글 로그인 (DDP 서버)
def google_login(db: Session, user_info: UserCreate) -> TokenResponse:
    # 1. 회원가입 또는 기존 유저 조회
    user = register(db, user_info, LoginMethod.GOOGLE)

    # 2. 토큰 발급
    access_token = create_access_token(user.user_id)
    refresh_token = create_refresh_token(user.user_id)
    save_refresh_token(
        db,
        user_id=user.user_id,
        refresh_token=refresh_token,
        expires_at=datetime.now(ZoneInfo("Asia/Seoul")) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.user_id,
        email=user.email,
        nickname=user.nickname
    )


# =========
# 로그아웃
# =========
def logout(db: Session, refresh_token: str) -> bool:
    # 1. DB 조회 전
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="refresh 토큰이 아닙니다")
    
    # 2. 해시 후 DB 조회
    hashed = hash_refresh_token(refresh_token)
    token = CRUDToken.get_by_refresh(db, hashed)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="토큰을 찾을 수 없습니다"
            )
    if token.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="이미 로그아웃된 토큰입니다"
            )
    
    # 3. revoked=True
    CRUDToken.set_revoked(db, hashed)
    return True

