import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import SensorHealthStatus


class SensorHealthBase(BaseModel):
    max30102_status: SensorHealthStatus = SensorHealthStatus.UNKNOWN
    dht11_status: SensorHealthStatus = SensorHealthStatus.UNKNOWN
    mpu6050_status: SensorHealthStatus = SensorHealthStatus.UNKNOWN
    gps_status: SensorHealthStatus = SensorHealthStatus.UNKNOWN
    details: dict[str, Any] | None = None


class SensorHealthCreate(SensorHealthBase):
    measurement_id: uuid.UUID | None = None
    device_id: uuid.UUID
    checked_at: datetime | None = None


class SensorHealthResponse(SensorHealthBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    measurement_id: uuid.UUID | None = None
    device_id: uuid.UUID
    checked_at: datetime
    created_at: datetime
