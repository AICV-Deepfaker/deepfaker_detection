from sqlalchemy.orm import Session, joinedload
from models.models import User, LoginMethod, Token, Video, VideoStatus, Source, Result, FastReport, DeepReport, Alert
from datetime import date, datetime

# ====================================================
# User CRUD
# ====================================================

# ==============
# 생성 (Create)
# ==============

# 사용 : 회원가입
def create_user(db: Session, user_info: dict): 
    """ 유저 생성 """
    db_user = User( # 객체
        email = user_info['email'],
        login_method = LoginMethod.local,
        hashed_password = user_info['hashed_password'], # service에서 입력
        name = user_info['name'],
        nickname = user_info['nickname'],
        birth = user_info['birth'],
        profile_image = user_info.get('profile_image'), # s3 url, option
        affiliation = user_info.get('affiliation'), # option
        activation_points = 0    
    )
    
    db.add(db_user) #db_user에 추가
    db.commit() # DB에 저장
    db.refresh(db_user) # DB에서 다시 읽기
    return db_user

# ==============
# 조회 (Read)
# ==============

# 사용 : 회원가입, 로그인, 회원정보수정, 포인트 조회
def get_user_by_email(db: Session, email: str):
    """ 이메일 조회 """
    return db.query(User).filter(User.email == email).first() # email이 해당되는 행 전체조회 (비밀번호 포함)

# 사용 : 회원가입 
def get_user_by_nickname(db: Session, nickname: str):
    """ 닉네임 중복 체크 """
    return db.query(User).filter(User.nickname == nickname).first()

# 사용 : user_id로 조회
def get_user_by_id(db: Session, user_id: int): # 공통
    """ user_id로 유저 조회 """
    return db.query(User).filter(User.user_id == user_id).first()

# 사용 : 아이디 찾기
def get_user_by_name_birth(db: Session, name: str, birth: date):
    """ 이름, 생년월일 조회 """
    return db.query(User).filter(User.name == name, User.birth == birth).first()

# 사용 : 비밀번호 찾기
def get_user_by_name_birth_email(db: Session, name: str, birth, email: str): 
    """ 이름, 생년월일, 이메일 조회 """
    return db.query(User).filter(User.name == name, User.birth == birth, User.email == email).first()

# ==============
# 수정 (Update)
# ==============

# 사용 : 회원정보수정
def update_user(db: Session, email: str, update_info: dict):
    """ 유저 정보 변경 """
    user = get_user_by_email(db, email)

    if update_info.get('hashed_password') is not None: # pw
        user.hashed_password = update_info['hashed_password']
    if update_info.get('profile_image') is not None: # 프로필
        user.profile_image = update_info['profile_image']
    if update_info.get('affiliation') is not None: # 소속
        user.affiliation = update_info['affiliation']

    db.commit()
    db.refresh(user)
    return user

# 사용 : 포인트 업데이트
def update_active_points(db: Session, user_id: int, points: int):
    """ 포인트 업데이트 """
    user = get_user_by_id(db, user_id)
    user.active_points += points # 1000점
    db.commit()
    db.refresh(user)
    return user.activation_points

# ==============
# 삭제 (Delete)
# ==============

# 사용 : 회원탈퇴
def delete_user(db: Session, email: str):
    """ 유저 삭제 """
    user = get_user_by_email(db, email)
    db.delete(user)
    db.commit()
    return True




# ====================================================
# Token CRUD
# ====================================================

# ==============
# 생성 (Create)
# ==============

# 사용 : 로그인
def create_token(db: Session, token_info: dict): 
    """ 토큰 저장 """
    db_token = Token( #객체
        user_id=token_info['user_id'],
        refresh_token=token_info['refresh_token'],
        # device_uuid=token_info.get('device_uuid'), // 기기 수집 (이후 개발 예정)
        expires_at=token_info['expires_at']
    )

    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token

# ==============
# 조회 (Read)
# ==============

# 사용 : refresh 토큰 갱신 (access_token은 DB 접근 X), 로그아웃(revoked 조회)
def get_token_by_refresh(db: Session, refresh_token: str): 
    """ refresh token으로 토큰 조회 """
    return db.query(Token).filter(Token.refresh_token == refresh_token).first()

# ==============
# 수정 (Update)
# ==============

# 사용 : 로그아웃
def update_revoked(db: Session, refresh_token: str): 
    """ 토큰 비활성화 """
    token = get_token_by_refresh(db, refresh_token)
    token.revoked = True
    db.commit()
    return True




# ====================================================
# Video CRUD
# ====================================================

# ==============
# 생성 (Create)
# ==============

# 사용 : 비디오 url/업로드 입력
def create_video(db: Session, video_info: dict): 
    """ 비디오 생성 """
    db_video = Video( # 객체
        user_id=video_info['user_id'],
        origin_path=video_info['origin_path'],
        source_url=video_info.get('source_url'),  # 링크 입력 시
        status=VideoStatus.pending
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video) # video_id 포함
    return db_video # video_id가 채워진 객체 반환

# ==============
# 조회 (Read)
# ==============

# def get_video_by_id(db: Session, video_id: int): # 필요시 주석 해제
#     """ video_id로 비디오 조회 """
#     return db.query(Video).filter(Video.video_id == video_id).first()

# 사용 : 히스토리(url)
def get_videos_by_user(db: Session, user_id: int): 
    """ 유저의 모든 비디오 조회 """
    return db.query(Video).filter(Video.user_id == user_id).all()

# ==============
# 수정 (Update)
# ==============

# 사용 : 영상 분석 상태 업로드
def update_video_status(db: Session, video_id: int, status: VideoStatus): 
    """ 비디오 상태 업데이트 """
    video = db.query(Video).filter(Video.video_id == video_id).first() # video_id로 조회
    video.status = status # 상태 업로드 (pending, processing, completed, failed)
    db.commit()
    db.refresh(video) 
    return video 



# ====================================================
# Source CRUD
# ====================================================

# ==============
# 생성 (Create)
# ==============

# 사용 : s3 업로드 후 video_id와 함께 저장
def create_source(db: Session, source_info: dict): 
    """ S3 경로 저장 """
    db_source = Source(
        video_id=source_info['video_id'],
        s3_path=source_info['s3_path'],
        expires_at=source_info['expires_at']
    )
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return db_source 


# ==============
# 조회 (Read)
# ==============

# 사용 : 영상 재호출(분석 실패 시)
def get_source_by_video(db: Session, video_id: int): 
    """ video_id로 S3 경로 조회 """
    return db.query(Source).filter(Source.video_id == video_id).first()



# ====================================================
# Result CRUD
# ====================================================

# ==============
# 생성 (Create)
# ==============

# 사용 : AI 분석 결과 저장
def create_result(db: Session, result_info: dict):
    """ 분석 결과 생성 """
    db_result = Result(
        user_id=result_info['user_id'],
        video_id=result_info['video_id'],
        is_fast=result_info['is_fast'],
        is_fake=result_info['is_fake']
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

# ==============
# 조회 (Read)
# ==============

# 사용 : 히스토리, 상세결과 조회, 공유 페이지
def get_result_by_id(db: Session, result_id: int):
    """ result_id로 결과 조회 """
    return db.query(Result).filter(Result.result_id == result_id).first()


# 참조 : 링크를 상세결과에만 포함할 경우
#       아래의 쿼리 대신 result.video.source_url 사용 (in service.py)

# 사용 : 히스토리 목록에 링크 첨부 (필요시)       
# def get_result_with_video(db: Session, result_id: int):
#     """ result_id로 결과 + 비디오(링크 호출용) 조회 """
#     return db.query(Result)\
#              .options(joinedload(Result.video))\
#              .filter(Result.result_id == result_id)\
#              .first()

# ==============
# 삭제 (Delete)
# ==============

# 사용 : 히스토리 삭제
def delete_result(db: Session, result_id: int): 
    """ 결과 삭제 (FastReport, DeepReport 함께 삭제) """
    result = get_result_by_id(db, result_id)
    db.delete(result)
    db.commit()
    return True


# ====================================================
# FastReport CRUD & DeepReport CRUD
# ====================================================

# ==============
# 생성 (Create)
# ==============

# 사용 : FastReport 저장
def create_fast_report(db: Session, report_info: dict): 
    """ Fast 분석 리포트 생성 """
    db_report = FastReport(
        user_id=report_info['user_id'],
        result_id=report_info['result_id'],
        freq_result=report_info['freq_result'],
        freq_conf=report_info['freq_conf'],
        freq_image=report_info['freq_image'],
        rppg_result=report_info['rppg_result'],
        rppg_conf=report_info['rppg_conf'],
        rppg_image=report_info['rppg_image'],
        stt_keyword=report_info['stt_keyword'],
        stt_risk_level=report_info['stt_risk_level'],
        stt_script=report_info['stt_script']
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

# 사용 : DeepReport 저장
def create_deep_report(db: Session, report_info: dict): 
    """ Deep 분석 리포트 생성 """
    db_report = DeepReport(
        user_id=report_info['user_id'],
        result_id=report_info['result_id'],
        unite_result=report_info['unite_result'],
        unite_conf=report_info['unite_conf']
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

# ==============
# 조회 (Read)
# ==============

# 사용 : FastReport 상세 결과 조회
def get_fast_report_by_result(db: Session, result_id: int): 
    """ result_id로 Fast 리포트 조회 """
    return db.query(FastReport).filter(FastReport.result_id == result_id).first()

# 사용 : DeepReport 상세 결과 조회
def get_deep_report_by_result(db: Session, result_id: int): 
    """ result_id로 Deep 리포트 조회 """
    return db.query(DeepReport).filter(DeepReport.result_id == result_id).first()


# ====================================================
# Alert CRUD
# ====================================================

# ==============
# 생성 (Create)
# ==============

# 사용 : 신고하기
def create_alert(db: Session, alert_info: dict): 
    """ 신고 생성 """
    db_alert = Alert(
        user_id=alert_info['user_id'],
        result_id=alert_info['result_id']
    )
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

# ==============
# 조회 (Read)
# ==============

# 사용 : 신고 내역
def get_alerts_by_user(db: Session, user_id: int): 
    """ 유저의 신고 내역 조회 """
    return db.query(Alert).filter(Alert.user_id == user_id).all()