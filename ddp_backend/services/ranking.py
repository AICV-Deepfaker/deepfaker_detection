from sqlalchemy.ext.asyncio import AsyncSession
from schemas.ranking import UserRanking
from services.crud.ranking import get_top10_crud

async def get_top10_ranking(db: AsyncSession) -> list[UserRanking]:
    rows = await get_top10_crud(db)

    return [
        UserRanking(
            rank=i,
            nickname=row.nickname,
            activation_points=row.activation_points,
        )
        for i, row in enumerate(rows, start=1)
    ]