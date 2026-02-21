from datetime import date
from pydantic import BaseModel
from .enums import Affiliation


class UserCreate(BaseModel):
    email: str
    hashed_password: str
    name: str
    nickname: str
    birth: date
    profile_image: str | None = None
    affiliation: Affiliation | None = None


class UserUpdate(BaseModel):
    hashed_password: str | None = None
    profile_image: str | None = None
    affiliation: Affiliation | None = None