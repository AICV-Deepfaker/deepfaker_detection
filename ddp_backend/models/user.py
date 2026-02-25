from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from pydantic import EmailStr
from sqlmodel import Field, Relationship

from ddp_backend.core.database import Base
from ddp_backend.schemas.enums import Affiliation, LoginMethod

from .models import MAX_S3_LEN, CreatedTimestampMixin

if TYPE_CHECKING:
    from .alert import Alert
    from .models import (
        DeepReport,
        FastReport,
        Result,
        Token,
        Video,
    )

# 1. 공통 Base 모델 (가장 교집합이 되는 필드들)
class UserBase(Base):
    email: EmailStr = Field(max_length=255, unique=True, index=True)
    name: str = Field(min_length=2, max_length=100)
    nickname: str = Field(min_length=2, max_length=100, unique=True)
    birth: date | None = None
    profile_image: str | None = Field(default=None, max_length=MAX_S3_LEN)
    affiliation: Affiliation | None = None


# 2. 실제 데이터베이스 테이블 (Table=True)
class User(UserBase, CreatedTimestampMixin, table=True):
    __tablename__: str = "users" # type: ignore
    
    user_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    login_method: LoginMethod = Field(default=LoginMethod.LOCAL)
    hashed_password: str | None = Field(default=None, max_length=255)
    activation_points: int = Field(default=0)

    token: Token = Relationship(back_populates="user", cascade_delete=True)
    videos: list[Video] = Relationship(back_populates="user", cascade_delete=True)
    results: list[Result] = Relationship(back_populates="user", cascade_delete=True)
    fast_reports: list[FastReport] = Relationship(
        back_populates="user", cascade_delete=True
    )
    deep_reports: list[DeepReport] = Relationship(
        back_populates="user", cascade_delete=True
    )
    alerts: list[Alert] = Relationship(back_populates="user", cascade_delete=True)
