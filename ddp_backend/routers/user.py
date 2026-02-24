# 프론트 연결

from typing import Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlmodel.orm.session import Session

from ddp_backend.core.database import get_db
from ddp_backend.core.security import get_current_user
from ddp_backend.schemas.enums import LoginMethod
from ddp_backend.schemas.user import (
    CheckEmail,
    CheckNickname,
    DeleteProfileImage,
    DuplicateCheckResponse,
    FindId,
    FindIdResponse,
    FindPassword,
    UserCreate,
    UserCreateResponse,
    UserEdit,
    UserEditResponse,
    UserMeResponse,
    UserRead,
)
from ddp_backend.services.user import (
    check_email_duplicate,
    check_nickname_duplicate,
    delete_profile_image,
    delete_user,
    edit_user,
    find_id,
    find_password,
    register,
)

router = APIRouter(prefix="/user", tags=["user"])

# 내 정보 조회 (토큰 필요)
@router.get("/me", response_model=UserMeResponse)
def get_me_route(
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
):
    return UserMeResponse.model_validate(current_user)

# 이메일 중복 확인 (실시간 체크)
@router.post("/check-email", response_model=DuplicateCheckResponse)
def check_email_route(body: CheckEmail, db: Session = Depends(get_db)):
    return DuplicateCheckResponse(is_duplicate=check_email_duplicate(db, body.email))

# 닉네임 중복 확인 (실시간 체크)
@router.post("/check-nickname", response_model=DuplicateCheckResponse)
def check_nickname_route(body: CheckNickname, db: Session = Depends(get_db)):
    return DuplicateCheckResponse(is_duplicate=check_nickname_duplicate(db, body.nickname))

# 회원가입 - 이메일/닉네임 중복 확인 후 유저 생성 (로컬)
@router.post("/register", response_model=UserCreateResponse)
def register_route(user_info: UserCreate, db: Session = Depends(get_db)):
    return register(db, user_info, LoginMethod.LOCAL)

# 아이디 찾기 - 이름/생년월일로 이메일 조회 (마스킹 처리)
@router.post("/find-id", response_model=FindIdResponse)
def find_id_route(user_info: FindId, db: Session = Depends(get_db)):
    return find_id(db, user_info)

# 비밀번호 찾기 - 이름/생년월일/이메일 확인 후 임시 비밀번호 발송
@router.post("/find-password")
def find_password_route(user_info: FindPassword, db: Session = Depends(get_db)):
    return find_password(db, user_info)

# 회원정보수정 - multipart/form-data (비밀번호/소속/프로필이미지) (토큰 필요)
@router.patch("/edit", response_model=UserEditResponse)
async def edit_route(
    new_password: Optional[str] = Form(None),
    new_affiliation: Optional[str] = Form(None),
    new_profile_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
):
    update_info = UserEdit(
        new_password=new_password if new_password else None,
        new_affiliation=new_affiliation if new_affiliation else None,
    )
    return edit_user(db, current_user.user_id, update_info, profile_image_file=new_profile_image)

# 프로필 이미지 삭제 (토큰 필요)
@router.delete("/profile/delete", response_model=UserMeResponse)
def delete_profile_route(
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
):
    return delete_profile_image(db, current_user.user_id)

# 회원탈퇴 - 유저 삭제 (cascade로 관련 데이터 모두 삭제) (토큰 필요)
@router.delete("/withdraw")
def withdraw_route(
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
):
    return delete_user(db, current_user.user_id)
