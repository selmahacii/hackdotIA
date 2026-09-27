import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.repositories.base import BaseRepository


class DeviceRepository(BaseRepository[Device]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Device, session)

    async def get_by_uid(self, device_uid: str) -> Device | None:
        stmt = select(Device).where(Device.device_uid == device_uid)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_elderly(self, elderly_id: uuid.UUID) -> Sequence[Device]:
        stmt = select(Device).where(Device.elderly_id == elderly_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
