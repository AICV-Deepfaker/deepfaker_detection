# 테이블이 4개 정도이므로 하나의 파일로 테이블 구성

from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Enum, Boolean, Float, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base
import enum


# 1. Definition of Enum 
class LoginMethod(str, enum.Enum):
    local = "Local"
    google = "Google"

class Affiliation(str, enum.Enum):
    ind = "개인"
    org = "기관"
    com = "회사"

class VideoStatus(str, enum.Enum): # 필요하지 않을 경우 삭제
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class OriginPath(str, enum.Enum):
    link = "Link"
    upload = "Upload"

class DetectionResult(str, enum.Enum):
    real = "Real"
    fake = "Fake"
    unknown = "Unknown" # 필요하지 않을 경우 삭제


# 2. User table
class User(Base):
    __tablename__ = "users"
    user_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True) # 효율성을 위해 user만 index=True
    email = Column(String(255), unique=True, nullable=False)
    login_method = Column(Enum(LoginMethod), nullable=True)
    hashed_password = Column(String(255)) # 자체 로그인 시에만 사용
    name = Column(String(100), nullable=False)
    nickname = Column(String(100), unique=True, nullable=False)
    birth = Column(Date, nullable=False)
    profile_image = Column(String(500)) # 필요 없을 경우 삭제
    affiliation = Column(Enum(Affiliation), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# 3. Token table
class Token(Base):
    __tablename__ = "tokens"
    token_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE")) # ondelete = 유저 삭제 시 함께 삭제
    refresh_token = Column(String(255), unique=True, nullable=False)
    revoked = Column(Boolean, default=False) # 로그아웃 되었거나 보안상 차단된 토큰 -> True시 반드시 재로그인
    device_uuid = Column(String(255)) # 토큰 보안과 연관 (필요 없을 경우 삭제)
    expires_at = Column(DateTime, nullable=False) # 토큰 만료
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# 4. Video table (12시간이 지난 video 테이블, s3는 삭제)
class Video(Base):
    __tablename__ = "videos"
    video_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    result_id = Column(BigInteger, ForeignKey("results.result_id"))
    origin_path = Column(Enum(OriginPath), nullable=False)
    source_url = Column(String(500))
    s3_path = Column(String(500), nullable=False)
    status = Column(Enum(VideoStatus), server_default=VideoStatus.pending.value)
    expires_at = Column(DateTime) # 12시간 후 만료 (서버에서 입력)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# 5. Result table
class Result(Base):
    __tablename__ = "results"
    result_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    video_id = Column(BigInteger, ForeignKey("videos.video_id"))
    ### 수정 필요
    frequency_result = Column(String(255))
    frequency_conf = Column(Float)
    rppg_result = Column(String(255))
    rppg_conf = Column(Float)
    unite_result = Column(String(255))
    unite_conf = Column(Float)
    ###
    confidence_score = Column(Float, nullable=False)
    detection_result = Column(Enum(DetectionResult), nullable=False)
    result_path = Column(String(500), nullable=False) # pdf/png를 s3에 저장 필요 시
    created_at = Column(DateTime(timezone=True), server_default=func.now())