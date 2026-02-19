# core/security.py (비밀번호 암호화 및 JWT)
# passward hashing 및 로그인 성공 시 JWT 토큰을 생성하는 유틸리티 파일

# 자체 로그인은 보안 설정 -> 데이터 규격 -> 핵심 로직 -> API 경로 순서로 개발

from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from typing import Optional
from config import settings

# 비밀번호 암호화
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    hashed_password = pwd_context.hash(password)
    return hashed_password

def verify_password(plain_password: str, hased_password: str) -> bool:
    return pwd_context.verify(plain_password, hased_password)

# jwt 토큰 생성
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()

    # 토큰 유효시간 계산
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# jwt 토큰 검증
def decode_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.ALGORITHM)
        return payload
    except JWTError:
        return None # 유효하지 않은 토큰




# # --- 테스트 코드 (확인 후 지우셔도 됩니다) ---
# if __name__ == "__main__":
#     test_password = "my_password123"
    
#     # 1. 비밀번호 암호화 확인
#     hashed = get_password_hash(test_password)
#     print(f"1. 암호화된 비번: {hashed}")
    
#     # 2. 비밀번호 일치 확인
#     is_match = verify_password(test_password, hashed)
#     print(f"2. 비번 일치 여부: {is_match}") # True가 나와야 함
    
#     # 3. 토큰 생성 확인
#     test_data = {"sub": "test@example.com", "user_id": 1}
#     token = create_access_token(data=test_data)
#     print(f"3. 생성된 토큰: {token}")
    
#     # 4. 토큰 검증 확인
#     decoded = decode_token(token)
#     print(f"4. 해독된 내용: {decoded}") # test_data 내용이 보여야 함