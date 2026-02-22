from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ddp_backend.core.security import get_password_hash
from ddp_backend.core.mailer import send_temp_pwd
from ddp_backend.core.s3 import upload_image_to_s3, delete_image_from_s3, delete_video_from_s3

from ddp_backend.schemas.user import UserCreate, UserResponse, FindId, FindIdResponse, FindPassword, UserEdit, UserEditResponse, DeleteProfileImage
from ddp_backend.services.crud.user import CRUDUser, UserCreate as UserCreateCRUD, UserUpdate

import random, string


# 로그인, 로그아웃 -> auth.py

# =========
# 회원가입
# =========
def register(db: Session, user_info: UserCreate) -> UserResponse:
    # 1. 이메일 중복 확인
    if CRUDUser.get_by_email(db, user_info.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="이미 사용 중인 이메일입니다"
        )

    # 2. 닉네임 중복 확인
    if CRUDUser.get_by_nickname(db, user_info.nickname):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="이미 사용 중인 닉네임입니다"
        )
    
    # 3. 비밀번호 해싱
    hashed_password = get_password_hash(user_info.password)

    # 4. 유저 생성
    new_user = CRUDUser.create(db, UserCreateCRUD(
        email=user_info.email,
        hashed_password=hashed_password,
        name=user_info.name,
        nickname=user_info.nickname,
        birth=user_info.birth,
        profile_image=user_info.profile_image,
        affiliation=user_info.affiliation
    ))

    return UserResponse(
        user_id=new_user.user_id,
        email=new_user.email,
        name=new_user.name,
        nickname=new_user.nickname,
        created_at=new_user.created_at
    )

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
    if len(local) <=3: #이메일 아이디 3자 이하일 경우
        masked_local = local[:1] + "*" * (len(local) - 1) # 이메일아이디
    else:
        masked_local = local[:3] + "*" * (len(local) - 3)
    masked_domain = "*" * len(domain_name) # 도메인
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
    
    # 1. 임시 비밀번호 생성
    temp_password = ''.join(
        random.choices(
            string.ascii_letters + string.digits, k=10
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
    hashed = get_password_hash(temp_password)
    CRUDUser.update(db, user.user_id, UserUpdate(hashed_password=hashed))

    return True

# =========
# 회원 정보 수정
# =========
def edit_user(db: Session, user_id: int, update_info: UserEdit) -> UserEditResponse:
    user = CRUDUser.get_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="유저를 찾을 수 없습니다"
            )
    
    update_data = {}
    response = UserEditResponse()

    # 비밀번호 변경
    if update_info.new_password:
        update_data['hashed_password'] = get_password_hash(
            update_info.new_password
            )
        response.changed_password = True
    
    # 프로필 이미지 변경
    if update_info.new_profile_image:
        update_data['profile_image'] = update_info.new_profile_image
        # upload_image_to_s3(user.new_profile_image) # 개발 예정
        response.changed_profile_image = update_info.new_profile_image
    
    # 소속 변경
    if update_info.new_affiliation:
        update_data['affiliation'] = update_info.new_affiliation
        response.changed_affiliation = update_info.new_affiliation

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="변경할 정보가 없습니다"
            )

    CRUDUser.update(db, user_id, UserUpdate(
        hashed_password=update_data.get('hashed_password'),
        profile_image=update_data.get('profile_image'),
        affiliation=update_data.get('affiliation')
    ))
    return response

# =========
# 프로필 이미지 삭제
# =========
def delete_profile_image(db: Session, user_id: int) -> UserEditResponse:
    user = CRUDUser.get_by_id(db, user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다")
    if not user.profile_image:
        raise HTTPException(status_code=404, detail="프로필 이미지가 없습니다")
    
    # S3 변경
    # delete_image_from_s3(user.profile_image)  # 이후 개발 예정

    user.profile_image = None
    db.commit()
    db.refresh(user)
    if user.profile_image is None:
        return UserEditResponse(delete_profile_image=True)
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="이미지 삭제에 실패하였습니다"
            )

# =========
# 회원 탈퇴
# =========
def delete_user(db: Session, user_id: int) -> bool:
    user = CRUDUser.get_by_id(db, user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="유저를 찾을 수 없습니다")
    
    # 1. 프로필 이미지 S3 삭제 (이후 개발 예정)
    # if user.profile_image:
    #     delete_image_from_s3(user.profile_image)
    
    # 2. 비디오 S3 삭제 (이후 개발 예정)
    # for video in user.videos:
    #     if video.source:
    #         delete_video_from_s3(video.source.s3_path)
    
    # 3. 유저 삭제 (cascade로 관련 데이터 모두 삭제)
    CRUDUser.delete(db, user_id)
    return True