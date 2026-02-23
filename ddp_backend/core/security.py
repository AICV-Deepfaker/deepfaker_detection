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
from sqlalchemy.orm import Session
from pydantic import SecretStr

from ddp_backend.core.config import settings  # 수정
from ddp_backend.core.database import get_db
from ddp_backend.services.crud.user import CRUDUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =========
# jwt access 토큰 생성
# =========
def create_access_token(user_id: int, expires_delta: timedelta | None = None):
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS) # 기본값

    if expires_delta: # 만료기간을 따로 지정할 경우
        expire = datetime.now(timezone.utc) + expires_delta # 덮어씌움

    encoded_jwt = jwt.encode(
            {"user_id": user_id, "exp": expire, "type": "refresh"},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
    
    return encoded_jwt


# =========
# jwt refresh 토큰 생성
# =========
def create_refresh_token(user_id: int, expires_delta: timedelta | None = None):
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS) # 기본값

    if expires_delta: # 만료기간을 따로 지정할 경우
        expire = datetime.now(timezone.utc) + expires_delta # 덮어씌움

    encoded_jwt = jwt.encode(
            {"user_id": user_id, "exp": expire, "type": "refresh"},
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
        
    # 유저 체크
    user_id: int | None = payload.get("user_id")
    # 토큰을 가진 user_id가 없을 때
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다")
    # 정상 토큰인데 유저가 없을 때
    user = CRUDUser.get_by_id(db, user_id)  # 이제 int 확정
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="존재하지 않는 유저입니다")
    
    # 로그아웃된 토큰 사용 시
    if user.tokens and user.tokens.revoked:
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
    verify_password = pwd_context.verify(plain_password.get_secret_value(), hashed_password)
    return verify_password




# # --- 테스트 코드 (확인 후 지우셔도 됩니다) ---
# if __name__ == "__main__":
#     from datetime import datetime, timezone


#     test_password = "my_password123"
    
#     # 1. 비밀번호 암호화 확인
#     hashed = get_password_hash(test_password)
#     print(f"1. 암호화된 비번: {hashed}")
    
#     # 2. 비밀번호 일치 확인
#     is_match = verify_password(test_password, hashed)
#     print(f"2. 비번 일치 여부: {is_match}") # True가 나와야 함
    
#     # 3. 토큰 생성 확인
#     test_data = {"sub": "test@example.com", "user_id": 1}
#     a_token = create_access_token(data=test_data)
#     r_token = create_refresh_token(data=test_data)
#     print(f"3. 생성된 토큰: {a_token}, {r_token}")
   
    
#     # 4. 토큰 검증 확인
#     a_decoded = decode_token(a_token)
#     r_decoded = decode_token(r_token)
#     print(f"4. 해독된 내용: {a_decoded}, {r_decoded}") # test_data 내용이 보여야 함

#     print(f"{datetime.fromtimestamp(a_decoded['exp'], tz=timezone.utc)}, {datetime.fromtimestamp(r_decoded['exp'], tz=timezone.utc)}")