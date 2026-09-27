from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.elderly import ElderlyPerson
from app.repositories.base import BaseRepository


class ElderlyRepository(BaseRepository[ElderlyPerson]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ElderlyPerson, session)

    async def list_active(self) -> Sequence[ElderlyPerson]:
        stmt = select(ElderlyPerson).where(ElderlyPerson.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalars().all()
