import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DeviceStatus


class DeviceBase(BaseModel):
    device_uid: str = Field(..., max_length=100)
    name: str | None = Field(default=None, max_length=100)
    status: DeviceStatus = DeviceStatus.UNKNOWN
    firmware_version: str | None = Field(default=None, max_length=50)
    battery_level: float | None = None
    wifi_rssi: int | None = None
    capabilities: dict[str, Any] | None = None


class DeviceCreate(DeviceBase):
    elderly_id: uuid.UUID


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    status: DeviceStatus | None = None
    firmware_version: str | None = Field(default=None, max_length=50)
    battery_level: float | None = None
    wifi_rssi: int | None = None
    capabilities: dict[str, Any] | None = None
    last_seen_at: datetime | None = None


class DeviceResponse(DeviceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    elderly_id: uuid.UUID
    last_seen_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
