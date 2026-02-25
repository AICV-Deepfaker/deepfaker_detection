from sqlmodel.orm.session import Session
from fastapi import HTTPException, status, UploadFile
from pydantic import SecretStr
from uuid import UUID

from ddp_backend.core.security import get_password_hash
from ddp_backend.core.mailer import send_temp_pwd
from ddp_backend.core.s3 import upload_image_to_s3, delete_image_from_s3, delete_video_from_s3, delete_video_from_s3
from ddp_backend.schemas.user import UserCreate, UserCreateCRUD, UserCreateResponse, UserMeResponse, FindId, FindIdResponse, FindPassword, UserEdit, UserEditResponse
from ddp_backend.schemas.enums import Affiliation

from ddp_backend.services.crud.user import CRUDUser, UserUpdate

from ddp_backend.schemas.enums import LoginMethod

import random, string


# 로그인, 로그아웃 -> auth.py

TEMP_STR_LEN=12 # 임시비밀번호 길이


# =========
# 닉네임 생성 (Google 전용, 필수)
# =========
def generate_nickname(db: Session, email: str) -> str:
    base = email.split("@")[0]
    while True:
        nickname = f"{base}_{random.randint(1000, 9999)}"
        if not CRUDUser.get_by_nickname(db, nickname):
            return nickname

# =========
# 이메일 중복 확인
# =========
def check_email_duplicate(db: Session, email: str) -> bool:
    return CRUDUser.get_by_email(db, email) is not None

# =========
# 닉네임 중복 확인
# =========
def check_nickname_duplicate(db: Session, nickname: str) -> bool:
    return CRUDUser.get_by_nickname(db, nickname) is not None

# =========
# 회원가입
# =========
def register(
    db: Session,
    user_info: UserCreate,
    login_method: LoginMethod = LoginMethod.LOCAL,
    profile_image_file: UploadFile | None = None
) -> UserCreateResponse:
    # 1. 이미 가입된 유저인지 확인
    existing_user = CRUDUser.get_by_email(db, user_info.email)
    if existing_user:
        if existing_user.login_method != login_method:
            raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="소셜 로그인으로 가입된 이메일입니다"
            )
        if login_method == LoginMethod.GOOGLE:
            return UserCreateResponse.model_validate(existing_user)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 이메일입니다"
        )

    # 2. 닉네임 처리 (Google은 랜덤생성)
    if login_method == LoginMethod.GOOGLE:
        nickname = generate_nickname(db, user_info.email)
    else:
        if user_info.nickname is None:
            raise HTTPException(status_code=400, detail="닉네임은 필수입니다")
        nickname = user_info.nickname

    # 3. 로컬만 체크
    if login_method == LoginMethod.LOCAL:
        if user_info.password is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="비밀번호를 입력해주세요"
            )
        else:
            hashed_password = get_password_hash(user_info.password)
        if user_info.birth is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="생년월일을 입력해주세요"
            )
        if check_nickname_duplicate(db, nickname):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 사용 중인 닉네임입니다"
            )
    else:
        hashed_password = None

    # 4. 유저 생성 (프로필 이미지는 Google OAuth URL 또는 None)
    new_user = CRUDUser.create(db, UserCreateCRUD(
        email=user_info.email,
        login_method=login_method,
        hashed_password=hashed_password,
        name=user_info.name,
        nickname=nickname,
        birth=user_info.birth,
        profile_image=user_info.profile_image,  # Google OAuth: URL 문자열
        affiliation=user_info.affiliation,
    ))
    assert new_user.user_id is not None

    # 5. 프로필 이미지 파일 S3 업로드 (로컬 회원가입)
    if profile_image_file:
        image_url = upload_image_to_s3(profile_image_file, str(new_user.user_id))
        CRUDUser.update(db, new_user.user_id, UserUpdate(profile_image=image_url))
        db.refresh(new_user)

    return UserCreateResponse.model_validate(new_user)

# =========
# 아이디 찾기
# =========
def find_id(db:Session, user_info: FindId) -> FindIdResponse:
    user = CRUDUser.get_by_name_birth(
        db,
        user_info.name,
        user_info.birth
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="아이디를 찾을 수 없습니다"
            )

    # 마스킹
    local, domain = user.email.rsplit("@", 1)
    domain_name, extension = domain.rsplit(".", 1)
    if len(local) <=3:
        masked_local = local[:1] + "*" * (len(local) - 1)
    else:
        masked_local = local[:3] + "*" * (len(local) - 3)
    masked_domain = "*" * len(domain_name)
    masked_email = masked_local + "@" + masked_domain + "." + extension

    return FindIdResponse(email=masked_email)

# 비밀번호 찾기
def find_password(db: Session, user_info: FindPassword) -> bool:
    user = CRUDUser.get_by_name_birth_email(
        db,
        user_info.name,
        user_info.birth,
        user_info.email
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="유저를 찾을 수 없습니다"
            )
    assert user.user_id is not None

    if user.login_method != LoginMethod.LOCAL:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail="소셜 로그인 계정입니다"
            )

    # 1. 임시 비밀번호 생성
    temp_password = ''.join(
        random.choices(
            string.ascii_letters + string.digits, k=TEMP_STR_LEN
            ))

    # 2. 이메일 발송 (실패하면 DB 갱신하지 않음)
    try:
        send_temp_pwd(user_info.email, temp_password)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이메일 발송에 실패했습니다"
            )

    # 3. DB 업데이트
    hashed = get_password_hash(SecretStr(temp_password))
    CRUDUser.update(db, user.user_id, UserUpdate(hashed_password=hashed))

    return True

# =========
# 회원 정보 수정
# =========
def edit_user(
    db: Session,
    user_id: UUID,
    update_info: UserEdit,
    profile_image_file: UploadFile | None = None
) -> UserEditResponse:
    user = CRUDUser.get_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="유저를 찾을 수 없습니다"
            )

    hashed_password: str | None = None
    profile_image: str | None = None
    affiliation: Affiliation | None = None

    # 비밀번호 변경
    changed_password = False
    if update_info.new_password:
        if user.login_method != LoginMethod.LOCAL:
            raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="소셜 로그인 계정은 비밀번호를 변경할 수 없습니다"
            )
        hashed_password = get_password_hash(update_info.new_password)
        changed_password = True

    # 프로필 이미지 변경 (파일 업로드 우선)
    if profile_image_file:
        # 기존 S3 이미지 삭제
        if user.profile_image and "amazonaws.com" in user.profile_image:
            delete_image_from_s3(user.profile_image)
        profile_image = upload_image_to_s3(profile_image_file, str(user_id))
    elif update_info.new_profile_image:
        profile_image = update_info.new_profile_image

    # 소속 변경
    if update_info.new_affiliation:
        affiliation = update_info.new_affiliation

    if not any([hashed_password, profile_image, affiliation]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="변경할 정보가 없습니다"
            )

    CRUDUser.update(db, user_id, UserUpdate(
        hashed_password=hashed_password,
        profile_image=profile_image,
        affiliation=affiliation
    ))
    db.refresh(user)
    return UserEditResponse(
        changed_password=changed_password,
        latest_user_info=UserMeResponse.model_validate(user)
    )


# =========
# 프로필 이미지 삭제
# =========
def delete_profile_image(db: Session, user_id: UUID) -> UserMeResponse:
    user = CRUDUser.get_by_id(db, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다")
    if not user.profile_image:
        raise HTTPException(status_code=404, detail="프로필 이미지가 없습니다")

    # S3에서 삭제
    if "amazonaws.com" in user.profile_image:
        delete_image_from_s3(user.profile_image)

    CRUDUser.delete_profile_image(db, user_id)
    db.refresh(user)
    return UserMeResponse.model_validate(user)


# =========
# 회원 탈퇴
# =========
def delete_user(db: Session, user_id: UUID) -> bool:
    user = CRUDUser.get_by_id(db, user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="유저를 찾을 수 없습니다")
    #삭제할 S3 key 모으기
    targets: list[str] = []

    # 1. 프로필 이미지 S3 삭제
    if user.profile_image:
        targets.append(user.profile_image)

    for video in getattr(user, "videos", []) or []:
        src = getattr(video, "source", None)
        if src and getattr(src, "s3_path", None):
            targets.append(src.s3_path)

    # S3 배치 삭제 (1000개 단위)
    # 실패해도 탈퇴 진행하고 싶으면 try/except 유지
    try:
        delete_keys_from_s3(targets)
    except Exception:
        pass

    # ✅ 3) DB 삭제 (cascade)
    CRUDUser.delete(db, user_id)
    return True
