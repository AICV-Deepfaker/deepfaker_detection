# schemas/user.py (데이터 규격 정의)
# Pydantic을 사용하여 회원가입 시 받을 이메일, 비밀번호 형식 등을 정의

from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime
from typing import Optional
from enum import Enum

# models.py에서 정의한 Enum
class LoginMethod(str, Enum):
    Local = "Local"
    Google = "Google"

class Affiliation(str, Enum):
    ind = "개인"
    org = "기관"
    com = "회사"

# 회원가입
class UserCreate(BaseModel):
    email : EmailStr
    password : str = Field(..., min_length=8) # 최소 8자 이상
    name : str = Field(..., min_length=2)
    nickname : str
    birth : date
    profile_image : Optional[str] = None
    affiliation : Optional[Affiliation] = None

# 로그인
class UserLogin(BaseModel):
    email : EmailStr
    password : str = Field(..., min_length=8) # 최소 8자 이상

# 회원정보 수정
class UserEdit(BaseModel): # 이외에 변경 불가
    profile_image : Optional[str] = None
    affiliation : Optional[Affiliation] = None

# 아이디 찾기
class FindId(BaseModel):
    name: str = Field(..., min_length=2)
    birth: date

# 비밀번호 찾기
class FindPassword(BaseModel):
    name: str = Field(..., min_length=2)
    birth: date
    email: EmailStr

