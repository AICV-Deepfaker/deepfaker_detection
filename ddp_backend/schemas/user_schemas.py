# schemas/user.py (데이터 규격 정의)
# Pydantic을 사용하여 회원가입 시 받을 이메일, 비밀번호 형식 등을 정의

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field

from .enums import Affiliation

__all__ = [
    "UserCreate",
    "CheckEmail",
    "CheckNickname",
    "UserLogin",
    "UserEdit",
    "FindId",
    "FindPassword",
    "UserResponse",
    "DuplicateCheckResponse",
    "TokenResponse",
    "UserEditResponse",
    "FindIdResponse",
]


# 회원가입
class UserCreate(BaseModel):  # Login_method는 서비스 로직에서
    email: EmailStr
    password: str = Field(..., min_length=8)  # 최소 8자 이상
    name: str = Field(..., min_length=2)
    nickname: str
    birth: date
    profile_image: str | None = None
    affiliation: Affiliation | None = None


class CheckEmail(BaseModel):  # 이메일 중복 확인 요청
    email: EmailStr


class CheckNickname(BaseModel):  # 닉네임 중복 확인 요청
    nickname: str = Field(..., min_length=2)


# 로그인
class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)  # 최소 8자 이상


# 회원정보 수정
class UserEdit(BaseModel):  # 이외에 변경 불가
    new_password: str | None = Field(None, min_length=8)  # 최소 8자 이상
    new_profile_image: str | None = None
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
class UserResponse(BaseModel):
    user_id: int
    email: EmailStr
    name: str
    nickname: str
    created_at: datetime


# 중복 확인 응답 (공통)
class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool


# 로그인 완료
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # jwt
    user_id: int
    email: EmailStr
    nickname: str


# 회원정보 수정 완료
class UserEditResponse(BaseModel):
    password_changed: bool = False
    profile_image_changed: str | None = None  # 수정 안 하면 None
    affiliation_changed: Affiliation | None = None


# 아이디 찾기
class FindIdResponse(BaseModel):
    email: str  # 마스킹된 문자열로 보낼 예정


# 비밀번호는 200만 반환하면 됨
