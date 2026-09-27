import uuid
from collections.abc import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.measurement import Measurement
from app.repositories.base import BaseRepository


class MeasurementRepository(BaseRepository[Measurement]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Measurement, session)

    async def get_by_event_id(self, event_id: uuid.UUID) -> Measurement | None:
        stmt = select(Measurement).where(Measurement.event_id == event_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_recent_by_device(
        self, device_id: uuid.UUID, limit: int = 50
    ) -> Sequence[Measurement]:
        stmt = (
            select(Measurement)
            .where(Measurement.device_id == device_id)
            .order_by(desc(Measurement.measured_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_recent_by_elderly(
        self, elderly_id: uuid.UUID, limit: int = 50
    ) -> Sequence[Measurement]:
        stmt = (
            select(Measurement)
            .where(Measurement.elderly_id == elderly_id)
            .order_by(desc(Measurement.measured_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
