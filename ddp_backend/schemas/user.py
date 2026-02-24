# schemas/user.py (데이터 규격 정의)
# Pydantic을 사용하여 회원가입 시 받을 이메일, 비밀번호 형식 등을 정의

from uuid import UUID

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr # 비밀번호 "***"로 표시
from .enums import  Affiliation

__all__ = [
    "UserCreate",
    "CheckEmail",
    "CheckNickname",
    "UserLogin",
    "UserEdit",
    "FindId",
    "FindPassword",
    "UserCreateResponse",
    "DuplicateCheckResponse",
    "TokenResponse",
    "UserMeResponse",
    "UserEditResponse",
    "FindIdResponse",
]




# 회원가입
class UserCreate(BaseModel):  # Login_method는 서비스 로직에서
    email: EmailStr
    password: SecretStr | None = Field(..., min_length=8)  # 최소 8자 이상 (구글은 비번이 없음-service에서 차단)
    name: str = Field(..., min_length=2)
    nickname: str | None = None # Service에서 모두 필수 입력으로 처리 (구글-랜덤생성                                                                          ㅠㅎ ㅍ)
    birth: date | None = None
    profile_image: str | None = None
    affiliation: Affiliation | None = None


# 이메일 중복 확인 요청
class CheckEmail(BaseModel):  
    email: EmailStr

# 닉네임 중복 확인 요청
class CheckNickname(BaseModel):  
    nickname: str = Field(..., min_length=2)


# 로그인
class UserLogin(BaseModel):
    email: EmailStr
    password: SecretStr = Field(..., min_length=8)  # 최소 8자 이상


# 회원정보 수정
class UserEdit(BaseModel):  # 이외에 변경 불가
    new_password: SecretStr | None = Field(None, min_length=8)  # 최소 8자 이상
    new_profile_image: str | None = None
    delete_profile_image: bool = False  # True면 이미지 삭제
    new_affiliation: Affiliation | None = None


# 아이디 찾기
class FindId(BaseModel):
    name: str = Field(..., min_length=2)
    birth: date


# 비밀번호 찾기
class FindPassword(BaseModel):  # 요청
    name: str = Field(..., min_length=2)
    birth: date
    email: EmailStr


# Response
# 회원가입 완료
class UserCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: EmailStr
    name: str
    nickname: str
    created_at: datetime


# 중복 확인 응답 (공통)
class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool

# 로그인 완료 : 토큰
class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # jwt
    user_id: UUID
    email: EmailStr
    nickname: str


# 내 정보 조회
class UserMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: EmailStr
    name: str
    nickname: str
    birth: date | None = None
    affiliation: Affiliation | None = None
    profile_image: str | None = None
    created_at: datetime


# 회원정보 수정 완료
class UserEditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    changed_password: bool = False
    latest_user_info : UserMeResponse

# 아이디 찾기
class FindIdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: str  # 마스킹된 문자열로 보낼 예정

# 비밀번호는 200만 반환하면 됨

# 탈퇴는 schema 없음

