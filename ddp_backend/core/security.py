# core/security.py (비밀번호 암호화 및 JWT)
# passward hashing 및 로그인 성공 시 JWT 토큰을 생성하는 유틸리티 파일

# 자체 로그인은 보안 설정 -> 데이터 규격 -> 핵심 로직 -> API 경로 순서로 개발

import os
import hashlib
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt, ExpiredSignatureError
from config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 비밀번호 암호화
def get_password_hash(password: str) -> str:
    hashed_password = pwd_context.hash(password)
    return hashed_password

# 비밀번호 검증
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# refresh token 암호화
def hash_refresh_token(token: str) -> str:
    salt = os.environ.get("REFRESH_TOKEN_SALT", "default_salt")
    return hashlib.sha256((token + salt).encode()).hexdigest()

# refresh token 검증
def verify_refresh_token(token: str, hashed_token: str) -> bool:
    return pwd_context.verify(token, hashed_token)

# jwt access 토큰 생성
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy() # {"user_id": 1} 복사
    # 토큰 유효시간 계산
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({ # {"user_id": 1, "exp": 만료시간} 추가
        "exp": expire, 
        "type": "access"
        }) 
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# jwt refresh 토큰 생성
def create_refresh_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "type": "refresh"
        })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# jwt 토큰 검증
def decode_token(token: str):
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
            )
        return payload
    
    except ExpiredSignatureError:
        raise ExpiredSignatureError("토큰이 만료되었습니다")

    except JWTError:
        raise JWTError("유효하지 않은 토큰입니다")



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