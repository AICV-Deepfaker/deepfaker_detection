from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ddp_backend.models.user import User


async def get_top10_crud(db: AsyncSession) -> list[User]:
    result = await db.exec(
        select(User)
        .order_by(desc(User.activation_points)) # type: ignore
        .limit(10)
    )
    return list(result.all())
