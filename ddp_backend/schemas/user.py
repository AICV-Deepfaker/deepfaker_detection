# schemas/user.py (데이터 규격 정의)
# 프론트엔드와 어떤 데이터를 주고받을지 약속하는 단계입니다.
# 정의: Pydantic을 사용하여 회원가입 시 받을 이메일, 비밀번호 형식 등을 정의합니다.
# 실제 적용: UserCreate (가입용), UserLogin (로그인용) 클래스를 작성합니다.

#from pydantic import BaseModel, EmailStr

# class UserCreate(BaseModel):
#     email: EmailStr
#     password: str