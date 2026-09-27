import uuid
from collections.abc import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sensor_health import SensorHealth
from app.repositories.base import BaseRepository


class SensorHealthRepository(BaseRepository[SensorHealth]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SensorHealth, session)

    async def get_by_measurement_id(self, measurement_id: uuid.UUID) -> SensorHealth | None:
        stmt = select(SensorHealth).where(SensorHealth.measurement_id == measurement_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_recent_by_device(
        self, device_id: uuid.UUID, limit: int = 50
    ) -> Sequence[SensorHealth]:
        stmt = (
            select(SensorHealth)
            .where(SensorHealth.device_id == device_id)
            .order_by(desc(SensorHealth.checked_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
