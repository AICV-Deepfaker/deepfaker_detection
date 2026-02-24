# core/security.py (JWT토큰, 비밀번호 암호화)
# passward hashing 및 로그인 성공 시 JWT 토큰을 생성하는 유틸리티 파일

# 자체 로그인은 보안 설정 -> 데이터 규격 -> 핵심 로직 -> API 경로 순서로 개발

import os
import hashlib
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt, ExpiredSignatureError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel.orm.session import Session
from pydantic import SecretStr

from uuid import UUID

from ddp_backend.core.config import settings  # 수정
from ddp_backend.core.database import get_db
from ddp_backend.services.crud.user import CRUDUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =========
# jwt access 토큰 생성
# =========
def create_access_token(user_id: UUID, expires_delta: timedelta | None = None):
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES) # 기본값

    if expires_delta: # 만료기간을 따로 지정할 경우
        expire = datetime.now(timezone.utc) + expires_delta # 덮어씌움

    encoded_jwt = jwt.encode(
            {
                "user_id": str(user_id),  # UUID는 반드시 문자열로 변환
                "exp": expire, 
                "type": "access"
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
    
    return encoded_jwt


# =========
# jwt refresh 토큰 생성
# =========
def create_refresh_token(user_id: UUID, expires_delta: timedelta | None = None):
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS) # 기본값

    if expires_delta: # 만료기간을 따로 지정할 경우
        expire = datetime.now(timezone.utc) + expires_delta # 덮어씌움

    encoded_jwt = jwt.encode(
            {
                "user_id": str(user_id), 
                "exp": expire, 
                "type": "refresh"
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
    
    return encoded_jwt


# =========
# refresh token 암호화
# =========
def hash_refresh_token(token: str) -> str: # 단방향 (sha256은 같은 토큰을 변환할 시 동일한 값 출력)
    salt = os.environ.get("REFRESH_TOKEN_SALT", "default_salt")
    return hashlib.sha256((token + salt).encode()).hexdigest()


# =========
# jwt 토큰 검증
# =========
def decode_token(token: str):
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
            )
        return payload
    
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었습니다")
    except JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")


# =========
# user 토큰 검증
# =========
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # 토큰 유효한지 체크
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="access 토큰이 아닙니다")
        
    # 토큰 내에 user_id가 없는 경우
    user_id_str: str | None = payload.get("user_id") # payload.get("user_id") = 문자열 반환
    if user_id_str is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다")  # 토큰에 user_id 필드가 없음

    # 유저 체크 # 유효 토큰인데 유저가 없을 때
    try:
        user_id = UUID(user_id_str) # str -> UUID 변환
    except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다")
    user = CRUDUser.get_by_id(db, user_id)  # DB의 user_io 호출
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="존재하지 않는 유저입니다")
    
    # 로그아웃된 토큰 사용 시
    if user.token and user.token.revoked:
        raise HTTPException(status_code=401, detail="비정상적인 접근입니다. 다시 로그인해주세요")
    
    return user # 보통 객체를 받아서 라우터 내부에서 user_id 뽑음


# =========
# 비밀번호 암호화
# =========
def get_password_hash(password: SecretStr) -> str:
    hashed_password = pwd_context.hash(password.get_secret_value())
    return hashed_password


# =========
# 비밀번호 검증
# =========
def verify_password(plain_password: SecretStr, hashed_password: str) -> bool:
    verify_pwd = pwd_context.verify(plain_password.get_secret_value(), hashed_password)
    return verify_pwd


