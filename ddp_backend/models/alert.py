import uuid
from datetime import datetime
from typing import Annotated, TYPE_CHECKING

from pydantic.types import AwareDatetime
from sqlalchemy import BigInteger, DateTime
from sqlmodel import Column, Field, Relationship

from ddp_backend.core.database import Base

if TYPE_CHECKING:
    from .user import User
    from .models import Result


class AlertBase(Base):
    user_id: uuid.UUID = Field(foreign_key="users.user_id", ondelete="CASCADE")
    result_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="results.result_id",
        ondelete="SET NULL",
        nullable=True,
    )
    
# 8. Alerts table
class Alert(AlertBase, table=True):
    __tablename__: str = "alerts"  # type: ignore
    alert_id: int | None = Field(default=None, primary_key=True, sa_type=BigInteger)
    alerted_at: Annotated[datetime, AwareDatetime] = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    user: "User" = Relationship(back_populates="alerts")
    result: "Result" = Relationship(back_populates="alerts", passive_deletes=True)