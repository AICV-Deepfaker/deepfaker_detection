# 프론트 연결

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ddp_backend.core.database import get_db
from ddp_backend.core.security import get_current_user
from ddp_backend.schemas.user import (
    UserCreate, UserResponse,
    FindId, FindIdResponse,
    FindPassword,
    UserEdit, UserEditResponse,
    DeleteProfileImage
)
from ddp_backend.services.user import (
    register, edit_user, delete_user,
    find_id, find_password, delete_profile_image
)

router = APIRouter(prefix="/user", tags=["user"])

# 회원가입 - 이메일/닉네임 중복 확인 후 유저 생성
@router.post("/register", response_model=UserResponse)
def register_route(user_info: UserCreate, db: Session = Depends(get_db)):
    return register(db, user_info)

# 아이디 찾기 - 이름/생년월일로 이메일 조회 (마스킹 처리)
@router.get("/find-id", response_model=FindIdResponse)
def find_id_route(user_info: FindId, db: Session = Depends(get_db)):
    return find_id(db, user_info)

# 비밀번호 찾기 - 이름/생년월일/이메일 확인 후 임시 비밀번호 발송
@router.post("/find-password")
def find_password_route(user_info: FindPassword, db: Session = Depends(get_db)):
    return find_password(db, user_info)

# 회원정보수정 - 비밀번호/프로필이미지/소속 변경 (토큰 필요)
@router.patch("/edit", response_model=UserEditResponse)
def edit_route(
    update_info: UserEdit,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    return edit_user(db, user_id, update_info)

# 프로필 이미지 삭제 - delete_profile_image=True 요청 시 이미지 삭제 (토큰 필요)
@router.delete("/profile", response_model=UserEditResponse)
def delete_profile_route(
    request: DeleteProfileImage,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    if not request.delete_profile_image:
        raise HTTPException(status_code=400, detail="삭제 요청이 아닙니다")
    return delete_profile_image(db, user_id)

# 회원탈퇴 - 유저 삭제 (cascade로 관련 데이터 모두 삭제) (토큰 필요)
@router.delete("/withdraw")
def withdraw_route(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    return delete_user(db, user_id)