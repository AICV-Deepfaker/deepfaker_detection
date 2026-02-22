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

from core.security import pwd_context, create_access_token, create_refresh_token, decode_token


from ddp_backend.schemas.user import UserLogin, TokenResponse # from router
from crud import get_user_by_email, get_token_by_refresh, update_last_used

# 토큰 갱신

def reissue_token(db: Session, refresh_token: str, last_used_at: datetime):
    token = get_token_by_refresh(db, refresh_token) # a row from token table

    if token or token.revoked:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
    
    #1.refresh 유효 -> access만 갱신
    if datetime.now(timezone.utc) < token.expires_at:
        new_access_token = create_access_token({"user_id": token.user_id}) # data: {} 
        update_last_used(db, token.user_id, datetime.now(timezone.utc))

# 1. access 토큰 갱신: access 만료, refresh 활성

# 2. refresh 토큰 갱신: refresh 만료, last_used_at 이후 30일 이내 앱 재사용

# 3. revoked = True : refresh 만료, last_used_at 이후 30일 초과
# def renew_token(db: Session, refresh_token: str):
#     token = get_token_by_refresh(db, refresh_token)
    
#     if not token or token.revoked:
#         raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
    
#     # refresh 유효할 때 → access만 갱신
#     if datetime.now(timezone.utc) < token.expires_at:
#         new_access_token = create_access_token({"user_id": token.user_id})
#         update_last_used(db, token.user_id, datetime.now(timezone.utc))
#         return {"access_token": new_access_token}
    
#     # refresh 만료됐을 때 → last_used_at 확인
#     user = get_user_by_id(db, token.user_id)
#     if user.last_used_at and datetime.now(timezone.utc) - user.last_used_at < timedelta(days=30):
#         # 30일 이내 → refresh, access 둘 다 갱신
#         new_access_token = create_access_token({"user_id": token.user_id})
#         new_refresh_token = create_refresh_token({"user_id": token.user_id})
#         update_last_used(db, token.user_id, datetime.now(timezone.utc))
#         # 새 refresh_token DB 저장
#         ...
#         return {"access_token": new_access_token, "refresh_token": new_refresh_token}
    
#     # 30일 초과 → 재로그인
#     raise HTTPException(status_code=401, detail="세션이 만료되었습니다. 다시 로그인해주세요")



# 로그인
def login(db:Session, user_info: UserLogin) -> TokenResponse:
    # 1. 유저 조회
    user = get_user_by_email




# services/auth_service.py
# from datetime import datetime, timedelta
# from core.config import settings
# from crud import user_crud, token_crud
# from schemas.user import UserLogin, TokenResponse


# auth_service.py



# def login(db: Session, user_info: UserLogin) -> TokenResponse:
#     # 1. 유저 조회
#     user = user_crud.get_user_by_email(db, user_info.email)
#     if not user:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="존재하지 않는 이메일입니다")
    
#     # 2. 비밀번호 확인
#     if not pwd_context.verify(user_info.password, user.hashed_password):
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="비밀번호가 올바르지 않습니다")
    
#     # 3. 토큰 발급
#     access_token = create_access_token({"user_id": user.user_id})
#     refresh_token = create_refresh_token({"user_id": user.user_id})
    
#     # 4. refresh_token DB 저장
#     token_crud.create_token(db, {
#         "user_id": user.user_id,
#         "refresh_token": refresh_token,
#         "expires_at": datetime.utcnow() + timedelta(days=7)
#     })
    
#     return TokenResponse(
#         access_token=access_token,
#         refresh_token=refresh_token,
#         user_id=user.user_id,
#         email=user.email,
#         nickname=user.nickname
#     )

# def logout(db: Session, refresh_token: str) -> bool:
#     token = token_crud.get_token_by_refresh(db, refresh_token)
#     if not token:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="토큰을 찾을 수 없습니다")
    
#     token_crud.update_revoked(db, refresh_token)
#     return True