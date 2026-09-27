import uuid
from collections.abc import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.enums import AlertStatus
from app.repositories.base import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Alert, session)

    async def get_active_by_dedup_key(self, dedup_key: str) -> Alert | None:
        stmt = select(Alert).where(
            Alert.dedup_key == dedup_key,
            Alert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_elderly(
        self,
        elderly_id: uuid.UUID,
        status: AlertStatus | None = None,
        limit: int = 50,
    ) -> Sequence[Alert]:
        stmt = select(Alert).where(Alert.elderly_id == elderly_id)
        if status is not None:
            stmt = stmt.where(Alert.status == status)
        stmt = stmt.order_by(desc(Alert.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
