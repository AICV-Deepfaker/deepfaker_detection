# services/auth_service.py (비즈니스 로직)
# 로그인, 로그아웃 : 비밀번호 검증 및 토큰 생성
#

# def authenticate_user(db, email, password):
#     # 1. DB에서 사용자 찾기
#     # 2. security.py의 함수로 비번 비교하기
#     # 3. 맞으면 토큰 생성, 틀리면 에러 반환
#     pass


from sqlalchemy.orm import Session # DB 연결
from fastapi import HTTPException, status # 상태 코드
from datetime import datetime, timezone, timedelta

from core.config import settings
from core.security import hash_refresh_token, create_access_token, create_refresh_token, decode_token, verify_password

from ddp_backend.schemas.user import UserLogin, TokenResponse # from router
from crud import upsert_token, get_user_by_email, get_token_by_refresh, set_token_revoked

# 생성된 토큰 저장
def save_refresh_token(db, user_id, refresh_token, expires_at):
    hashed = hash_refresh_token(refresh_token)
    upsert_token(db, user_id, hashed, expires_at)

# 토큰 갱신
def reissue_token(db: Session, refresh_token: str):
    # JWT 검증
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")

    token = get_token_by_refresh(db, refresh_token) # a row from token table

    # refresh 토큰이 없을 때
    if not token:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
    
    # payload의 user_id와 token의 user_id와 일치하지 않을경우
    if payload.get("user_id") != token.user_id:
            raise HTTPException(status_code=401, detail="사용자 정보가 일치하지 않습니다")
        
    # 토큰 만료되었을 때 (refresh 토큰 30일 경과)
    if token.revoked:
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다. 다시 로그인해주세요")
    
    # refresh 유효
    if datetime.now(timezone.utc) < token.expires_at:
        new_access_token = create_access_token({"user_id": token.user_id}) 
        new_refresh_token = create_refresh_token({"user_id": token.user_id}) 
        save_refresh_token(
            db,
            user_id=token.user_id,
            refresh_token=new_refresh_token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        return {"access_token": new_access_token, "refresh_token": new_refresh_token}
    
    # refresh 만료 → 재로그인
    set_token_revoked(db, refresh_token)
    raise HTTPException(status_code=401, detail="세션이 만료되었습니다. 다시 로그인해주세요")


# 로그인
def login(db:Session, user_info: UserLogin) -> TokenResponse:
    # 1. 유저 조회 + 비밀번호 확인
    user = get_user_by_email(db, user_info.email)
    if not user or not verify_password(user_info.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 올바르지 않습니다")

    # 2. 토큰 발급
    access_token = create_access_token({"user_id": user.user_id})
    refresh_token = create_refresh_token({"user_id": user.user_id})

    # 3. refresh_token 해시 후 저장
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


# 로그아웃
def logout(db: Session, refresh_token: str) -> bool:
    # 1. 해시 후 조회
    hashed = hash_refresh_token(refresh_token)
    token = get_token_by_refresh(db, hashed)
    
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="토큰을 찾을 수 없습니다")
    if token.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이미 로그아웃된 토큰입니다")
    
    # 2. revoked=True
    set_token_revoked(db, hashed)
    return True
