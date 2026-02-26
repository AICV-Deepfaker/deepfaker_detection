from sqlmodel.orm.session import Session
from ddp_backend.schemas.ranking import UserRanking
from ddp_backend.services.crud import CRUDUser

def get_top10_ranking(db: Session) -> list[UserRanking]:
    rows = CRUDUser.get_top_10(db)

    return [
        UserRanking(
            rank=i,
            nickname=row.nickname,
            activation_points=row.activation_points,
        )
        for i, row in enumerate(rows, start=1)
    ]