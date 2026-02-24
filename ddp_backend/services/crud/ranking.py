from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import User


async def get_top10_crud(db: AsyncSession):
    result = await db.execute(
        select(User.nickname, User.activation_points)
        .order_by(desc(User.activation_points))
        .limit(10)
    )
    return result.fetchall()

