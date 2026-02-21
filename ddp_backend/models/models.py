# 테이블이 4개 정도이므로 하나의 파일로 테이블 구성

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Enum, Boolean, Float, Date, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base
import enum


# 0. Definition of Enum 
class LoginMethod(str, enum.Enum):
    local = "local"
    google = "google"

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
    link = "link"
    upload = "upload"

class STTRiskLevel(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"
    none = "none"


# 1. Users table
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
    active_points = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Relationships
    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="user", cascade="all, delete-orphan")
    fast_reports = relationship("FastReport", back_populates="user", cascade="all, delete-orphan")
    deep_reports = relationship("DeepReport", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")


# 2. Tokens table
class Token(Base):
    __tablename__ = "tokens"
    token_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE")) # ondelete = 유저 삭제 시 함께 삭제
    refresh_token = Column(String(255), unique=True, nullable=False)
    revoked = Column(Boolean, default=False) # 로그아웃 되었거나 보안상 차단된 토큰 -> True시 반드시 재로그인
    device_uuid = Column(String(255)) # 토큰 보안과 연관 (필요 없을 경우 삭제)
    expires_at = Column(DateTime, nullable=False) # 토큰 만료
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Relationships
    user = relationship("User", back_populates="tokens")

# 3. Videos table
class Video(Base):
    __tablename__ = "videos"
    video_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    origin_path = Column(Enum(OriginPath), nullable=False)
    source_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Relationships
    user = relationship("User", back_populates="videos")
    sources = relationship("Source", back_populates="video", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="video", cascade="all, delete-orphan")

# 4. Sources table (12시간이 지난 video 테이블, s3는 삭제)
class Source(Base): # S3 관리용 (일정 시간 후 삭제 대상)
    __tablename__ = "sources"
    source_id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_id = Column(BigInteger, ForeignKey("videos.video_id", ondelete="CASCADE"))
    s3_path = Column(String(500), nullable=False)
    status = Column(Enum(VideoStatus), server_default=VideoStatus.pending.value)
    expires_at = Column(DateTime, nullable=False) # 12시간 후 만료 등
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Relationships
    video = relationship("Video", back_populates="sources")

# 5. Results table
class Result(Base):
    __tablename__ = "results"
    result_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    video_id = Column(BigInteger, ForeignKey("videos.video_id", ondelete="CASCADE"))
    is_fast = Column(Boolean)
    is_fake = Column(Boolean)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Relationships
    user = relationship("User", back_populates="results")
    video = relationship("Video", back_populates="results")
    fast_report = relationship("FastReport", back_populates="result", uselist=False)
    deep_report = relationship("DeepReport", back_populates="result", uselist=False)
    alerts = relationship("Alert", back_populates="result")
    

# 6. FastReports table
class FastReport(Base):
    __tablename__ = "fast_reports"
    fast_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    result_id = Column(BigInteger, ForeignKey("results.result_id", ondelete="CASCADE"))
    freq_result = Column(String(255), nullable=False)
    freq_conf = Column(Float, nullable=False)
    freq_image = Column(String(255), nullable=False)
    rppg_result = Column(String(255), nullable=False)
    rppg_conf = Column(Float, nullable=False)
    rppg_image = Column(String(255), nullable=False)
    stt_keyword = Column(String(255), nullable=False)
    stt_risk_level = Column(Enum(STTRiskLevel))
    stt_script = Column(JSON, nullable=False)
    # Relationships
    user = relationship("User", back_populates="fast_reports")
    result = relationship("Result", back_populates="fast_report")

# 7. DeepReports table
class DeepReport(Base):
    __tablename__ = "deep_reports"
    deep_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    result_id = Column(BigInteger, ForeignKey("results.result_id", ondelete="CASCADE"))
    unite_result = Column(String(255), nullable=False)
    unite_conf = Column(Float, nullable=False)
    # Relationships
    user = relationship("User", back_populates="deep_reports")
    result = relationship("Result", back_populates="deep_report")

# 8. Alerts table
class Alert(Base): # 신고하기
    __tablename__ = "alerts"
    alert_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    result_id = Column(BigInteger, ForeignKey("results.result_id", ondelete="CASCADE"))
    alerted_at = Column(DateTime(timezone=True), server_default=func.now())
    # Relationships
    user = relationship("User", back_populates="alerts")
    result = relationship("Result", back_populates="alerts")
    