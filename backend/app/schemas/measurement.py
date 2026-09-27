import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MeasurementBase(BaseModel):
    event_id: uuid.UUID | None = None
    measured_at: datetime
    bpm: float | None = Field(default=None, ge=0, le=300)
    spo2: float | None = Field(default=None, ge=0, le=100)
    finger_detected: bool = False
    temperature_c: float | None = Field(default=None, ge=-20, le=100)
    humidity_percent: float | None = Field(default=None, ge=0, le=100)
    accel_x_g: float | None = None
    accel_y_g: float | None = None
    accel_z_g: float | None = None
    accel_magnitude_g: float | None = None
    gps_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    gps_longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    gps_fix_valid: bool = False
    battery_level: float | None = Field(default=None, ge=0, le=100)
    wifi_rssi: int | None = None


class MeasurementCreate(MeasurementBase):
    device_id: uuid.UUID
    elderly_id: uuid.UUID
    received_at: datetime | None = None


class MeasurementResponse(MeasurementBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: uuid.UUID
    elderly_id: uuid.UUID
    received_at: datetime
    created_at: datetime
