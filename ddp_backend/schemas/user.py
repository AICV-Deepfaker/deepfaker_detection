# schemas/user.py (데이터 규격 정의)
# Pydantic을 사용하여 회원가입 시 받을 이메일, 비밀번호 형식 등을 정의
import uuid
from datetime import date, datetime

from pydantic import (  # 비밀번호 "***"로 표시
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
)

from ddp_backend.models.user import UserBase

from .enums import Affiliation, LoginMethod

__all__ = [
    "CheckEmail",
    "CheckNickname",
    "UserLogin",
    "UserEdit",
    "DeleteProfileImage",
    "FindId",
    "FindPassword",
    "UserCreateResponse",
    "UserCreateCRUD",
    "UserCreate",
    "UserMeResponse",
    "DuplicateCheckResponse",
    "TokenResponse",
    "UserEditResponse",
    "FindIdResponse",
]


# 3. DB 생성용 스키마 (Service -> Repository)
class UserCreateCRUD(UserBase):
    login_method: LoginMethod = LoginMethod.LOCAL
    hashed_password: str | None = None


# 회원가입 요청 (Base를 상속받아 필요한 것만 재정의/추가)
class UserCreate(UserBase):
    # Base에서는 필수지만, 가입 시에는 None 허용 (Service에서 처리)
    nickname: str | None = None  # type: ignore
    password: SecretStr | None = Field(..., min_length=8)


# 내 정보 조회 (UserBase의 모든 필드를 포함하므로 상속 활용)
class UserMeResponse(UserBase):
    user_id: uuid.UUID
    created_at: datetime


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


# 프로필 이미지 삭제
class DeleteProfileImage(BaseModel):
    delete_profile_image: bool = False


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

    user_id: uuid.UUID
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
    user_id: int
    email: EmailStr
    nickname: str


# 회원정보 수정 완료
class UserEditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    changed_password: bool = False
    changed_profile_image: str | None = None  # 프로필 이미지 업데이트
    deleted_profile_image: bool = False  # 프로필이미지 삭제 요청
    changed_affiliation: Affiliation | None = None  # 수정 안 하면 None


# 아이디 찾기
class FindIdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: str  # 마스킹된 문자열로 보낼 예정


# 비밀번호는 200만 반환하면 됨

# 탈퇴는 schema 없음
