"""Sensor Health API endpoints for hardware diagnostics and monitoring."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import AuthenticatedUser, get_current_user, get_db
from app.models.device import Device
from app.models.sensor_health import SensorHealth

router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.get("")
async def list_sensor_health(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    device_id: uuid.UUID | None = None,
) -> list[dict]:
    """Retrieve the latest sensor diagnostics and hardware integrity status for devices."""
    # Find relevant devices based on user role and isolation
    dev_stmt = select(Device).options(selectinload(Device.elderly))

    if current_user.role == "CAREGIVER" and current_user.assigned_elderly_ids:
        dev_stmt = dev_stmt.where(Device.elderly_id.in_(current_user.assigned_elderly_ids))

    if device_id:
        dev_stmt = dev_stmt.where(Device.id == device_id)

    devices_res = await session.execute(dev_stmt)
    devices = list(devices_res.scalars().all())

    results = []
    for dev in devices:
        # Get latest sensor health for this device
        sh_stmt = (
            select(SensorHealth)
            .where(SensorHealth.device_id == dev.id)
            .order_by(SensorHealth.checked_at.desc())
            .limit(1)
        )
        sh_res = await session.execute(sh_stmt)
        sh = sh_res.scalars().first()

        results.append(
            {
                "device_id": str(dev.id),
                "device_uid": dev.device_uid,
                "device_name": dev.name,
                "device_status": (
                    dev.status.value if hasattr(dev.status, "value") else str(dev.status)
                ),
                "elderly_id": str(dev.elderly_id),
                "elderly_name": (
                    f"{dev.elderly.first_name} {dev.elderly.last_name}"
                    if dev.elderly
                    else "Inconnu"
                ),
                "last_checked_at": (
                    sh.checked_at.isoformat()
                    if sh
                    else (dev.last_seen_at.isoformat() if dev.last_seen_at else None)
                ),
                "max30102_status": (
                    sh.max30102_status.value
                    if sh and hasattr(sh.max30102_status, "value")
                    else (str(sh.max30102_status) if sh else "UNKNOWN")
                ),
                "mpu6050_status": (
                    sh.mpu6050_status.value
                    if sh and hasattr(sh.mpu6050_status, "value")
                    else (str(sh.mpu6050_status) if sh else "UNKNOWN")
                ),
                "dht11_status": (
                    sh.dht11_status.value
                    if sh and hasattr(sh.dht11_status, "value")
                    else (str(sh.dht11_status) if sh else "UNKNOWN")
                ),
                "gps_status": (
                    sh.gps_status.value
                    if sh and hasattr(sh.gps_status, "value")
                    else (str(sh.gps_status) if sh else "UNKNOWN")
                ),
                "details": sh.details if sh else {},
            }
        )

    return results
