# 테이블이 4개 정도이므로 하나의 파일로 테이블 구성
from enum import Enum as _Enum
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import TYPE_CHECKING, Annotated, Optional # type: ignore

from pydantic.types import AwareDatetime
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
)
from sqlmodel import Field, Relationship

from ddp_backend.core.config import settings
from ddp_backend.core.database import Base
from ddp_backend.schemas.enums import (
    OriginPath,
    VideoStatus,
)
from ddp_backend.schemas.enums import Result as ResultEnum

if TYPE_CHECKING:
    from .alert import Alert
    from .user import User
    from .report import DeepReport, FastReport

MAX_S3_LEN = 512


# 0. source default expires_at : 12시간
# DB 내에 생성하면 DB 문법에 의존해야하므로 python 함수로 계산
def source_def_expire() -> datetime:
    return datetime.now(ZoneInfo("Asia/Seoul")) + timedelta(hours=12)

def enum_to_value(x: list[_Enum]):
    return [str(e.value) for e in x]

class CreatedTimestampMixin(Base):
    created_at: Annotated[datetime, AwareDatetime] = Field(
        default_factory=lambda: datetime.now(ZoneInfo("Asia/Seoul")),#lambda : 레코드 형성 때마다 새로 생성
        sa_type=DateTime(timezone=True), # type: ignore
    )


# 2. Tokens table
class Token(CreatedTimestampMixin, Base, table=True):
    __tablename__: str = "tokens"  # type: ignore
    token_id: int | None = Field(default=None, primary_key=True, sa_type=BigInteger)
    user_id: uuid.UUID = Field(foreign_key="users.user_id", ondelete="CASCADE")
    refresh_token: str = Field(max_length=255, unique=True)
    expires_at: Annotated[datetime, AwareDatetime] = Field(
        default_factory=lambda: datetime.now(ZoneInfo("Asia/Seoul")) +timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    revoked: bool = False

    user: "User" = Relationship(back_populates="token")


# 3. Videos table
class Video(CreatedTimestampMixin, Base, table=True):
    __tablename__: str = "videos"  # type: ignore
    video_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.user_id", ondelete="CASCADE")
    origin_path: OriginPath = Field(
        sa_column=Column(Enum(OriginPath, values_callable=enum_to_value), nullable=False),
    )
    source_url: str | None = Field(default=None, max_length=500)
    status: VideoStatus = Field(
        default=VideoStatus.PENDING,
        sa_column=Column(Enum(VideoStatus, values_callable=enum_to_value), nullable=False),
    )

    user: "User" = Relationship(back_populates="videos")
    source: "Source" = Relationship(back_populates="video", cascade_delete=True)
    result: "Result" = Relationship(back_populates="video", cascade_delete=True)


# 4. Sources table (12시간이 지난 video 테이블, s3는 삭제)
class Source(CreatedTimestampMixin, Base, table=True):
    __tablename__: str = "sources"  # type: ignore
    source_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    video_id: uuid.UUID = Field(foreign_key="videos.video_id", ondelete="CASCADE")
    s3_path: str = Field(max_length=MAX_S3_LEN)
    expires_at: Annotated[datetime, AwareDatetime] = Field(
        default_factory=source_def_expire,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    video: "Video" = Relationship(back_populates="source")


# 5. Results table
class Result(CreatedTimestampMixin, Base, table=True):
    __tablename__: str = "results"  # type: ignore
    result_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.user_id", ondelete="CASCADE")
    video_id: uuid.UUID = Field(
        foreign_key="videos.video_id", ondelete="CASCADE", unique=True
    )
    is_fast: bool
    total_result: ResultEnum

    user: "User" = Relationship(back_populates="results")
    video: "Video" = Relationship(back_populates="result")
    fast_report: Optional["FastReport"] = Relationship( # type: ignore
        back_populates="result", cascade_delete=True
    )
    deep_report: Optional["DeepReport"] = Relationship( # type: ignore
        back_populates="result", cascade_delete=True
    )
    alerts: list["Alert"] = Relationship(back_populates="result")
