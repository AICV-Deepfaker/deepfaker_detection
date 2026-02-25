from pydantic import BaseModel

class UserRanking(BaseModel):
    rank: int
    nickname: str
    activation_points: int