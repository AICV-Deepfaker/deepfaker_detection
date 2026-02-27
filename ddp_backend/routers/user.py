# 프론트 연결

from datetime import date

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlmodel import Session

from pydantic import SecretStr, EmailStr

from ddp_backend.core.database import get_db
from ddp_backend.core.security import get_current_user
from ddp_backend.core.s3 import to_public_url
from ddp_backend.models import User
from ddp_backend.schemas.enums import Affiliation, LoginMethod
from ddp_backend.schemas.user import (
    CheckEmail,
    CheckNickname,
    DuplicateCheckResponse,
    FindId,
    FindIdResponse,
    FindPassword,
    UserCreate,
    UserCreateResponse,
    UserEdit,
    UserEditResponse,
    UserMeResponse,
)
from ddp_backend.schemas.ranking import UserRanking
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
from ddp_backend.services.ranking import get_top10_ranking

router = APIRouter(prefix="/user", tags=["user"])

# 내 정보 조회 (토큰 필요)
@router.get("/me", response_model=UserMeResponse)
def get_me_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    me = UserMeResponse.model_validate(current_user)
    me.profile_image = to_public_url(current_user.profile_image)  # S3 key → 공개 URL
    return me

# 이메일 중복 확인 (실시간 체크)
@router.post("/check-email", response_model=DuplicateCheckResponse)
def check_email_route(body: CheckEmail, db: Session = Depends(get_db)):
    return DuplicateCheckResponse(is_duplicate=check_email_duplicate(db, body.email))

# 닉네임 중복 확인 (실시간 체크)
@router.post("/check-nickname", response_model=DuplicateCheckResponse)
def check_nickname_route(body: CheckNickname, db: Session = Depends(get_db)):
    return DuplicateCheckResponse(is_duplicate=check_nickname_duplicate(db, body.nickname))

# 회원가입 - multipart/form-data (이메일/닉네임 중복 확인 후 유저 생성, 프로필 이미지 S3 업로드)
@router.post("/register", response_model=UserCreateResponse)
async def register_route(
    email: EmailStr = Form(...),
    password: SecretStr = Form(...),
    name: str = Form(...),
    nickname: str | None = Form(None),
    birth: date | None = Form(None),
    affiliation: Affiliation | None = Form(None),
    profile_image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    user_info = UserCreate(
        email=email,
        password=password,
        name=name,
        nickname=nickname,
        birth=birth,
        affiliation=affiliation,
    )
    return register(db, user_info, LoginMethod.LOCAL, profile_image_file=profile_image)

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
    new_password: SecretStr | None = Form(None),
    new_affiliation: Affiliation | None = Form(None),
    new_profile_image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 소셜 계정 진입 차단
    if new_password and current_user.login_method != LoginMethod.LOCAL:
        raise HTTPException(status_code=403, detail="소셜 로그인 계정은 비밀번호를 변경할 수 없습니다.")

    update_info = UserEdit(
        new_password=new_password,
        new_affiliation=new_affiliation,
    )
    return edit_user(db, current_user.user_id, update_info, profile_image_file=new_profile_image)

# 프로필 이미지 삭제 (토큰 필요)
@router.delete("/profile/delete", response_model=UserMeResponse)
def delete_profile_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return delete_profile_image(db, current_user.user_id)

# 회원탈퇴 - 유저 삭제 (cascade로 관련 데이터 모두 삭제) (토큰 필요)
@router.delete("/withdraw")
def withdraw_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return delete_user(db, current_user.user_id)

# 포인트 랭킹 top10
@router.get("/top10", response_model=list[UserRanking])
def points_top10_ranking(db: Session = Depends(get_db)):
    return get_top10_ranking(db)