import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import DeviceStatus, SensorHealthStatus
from app.schemas.common import ensure_utc_datetime, strip_non_empty_str


class SensorTelemetryPayload(BaseModel):
    """Official IoT telemetry payload received from the ESP32 via MQTT.

    Validates physiological, environmental, kinematic, and spatial sensor values
    with strict range boundaries and cross-sensor integrity rules.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="1.0", max_length=10)
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    device_uid: str = Field(..., min_length=1, max_length=100)
    timestamp: datetime

    # MAX30102 Photoplethysmography sensor
    bpm: float | None = Field(default=None, ge=0.0, le=250.0)
    spo2: float | None = Field(default=None, ge=0.0, le=100.0)
    finger_detected: bool = False

    # DHT11 Environmental sensor (-40°C to 80°C range)
    temperature_c: float | None = Field(default=None, ge=-40.0, le=80.0)
    humidity_percent: float | None = Field(default=None, ge=0.0, le=100.0)

    # MPU6050 3-axis accelerometer (-8g to +8g hardware range)
    accel_x_g: float | None = Field(default=None, ge=-8.0, le=8.0)
    accel_y_g: float | None = Field(default=None, ge=-8.0, le=8.0)
    accel_z_g: float | None = Field(default=None, ge=-8.0, le=8.0)
    accel_magnitude_g: float | None = Field(default=None, ge=0.0, le=20.0)

    # GPS coordinates
    gps_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    gps_longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    gps_fix_valid: bool = False

    # Hardware status & connectivity
    battery_level: int | None = Field(default=None, ge=0, le=100)
    wifi_rssi: int | None = Field(default=None, ge=-120, le=0)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        return ensure_utc_datetime(v)

    @field_validator("device_uid")
    @classmethod
    def validate_device_uid(cls, v: str) -> str:
        return strip_non_empty_str(v)

    @model_validator(mode="after")
    def validate_cross_sensor_rules(self) -> "SensorTelemetryPayload":
        # Cross-validation 1: MAX30102 finger contact check
        if not self.finger_detected:
            if self.bpm is not None or self.spo2 is not None:
                raise ValueError("bpm and spo2 must be null when finger_detected is false")

        # Cross-validation 2: GPS satellite fix check
        if not self.gps_fix_valid:
            if self.gps_latitude is not None or self.gps_longitude is not None:
                raise ValueError(
                    "gps_latitude and gps_longitude must be null when gps_fix_valid is false"
                )

        return self


class DeviceStatusPayload(BaseModel):
    """Heartbeat and device status payload emitted by the ESP32."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="1.0", max_length=10)
    device_uid: str = Field(..., min_length=1, max_length=100)
    timestamp: datetime
    status: DeviceStatus
    battery_level: int | None = Field(default=None, ge=0, le=100)
    wifi_rssi: int | None = Field(default=None, ge=-120, le=0)
    firmware_version: str | None = Field(default=None, max_length=50)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        return ensure_utc_datetime(v)

    @field_validator("device_uid")
    @classmethod
    def validate_device_uid(cls, v: str) -> str:
        return strip_non_empty_str(v)


class SensorHealthPayload(BaseModel):
    """Self-test and hardware diagnostic payload for attached sensors."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="1.0", max_length=10)
    device_uid: str = Field(..., min_length=1, max_length=100)
    timestamp: datetime

    max30102_status: SensorHealthStatus = SensorHealthStatus.UNKNOWN
    dht11_status: SensorHealthStatus = SensorHealthStatus.UNKNOWN
    mpu6050_status: SensorHealthStatus = SensorHealthStatus.UNKNOWN
    gps_status: SensorHealthStatus = SensorHealthStatus.UNKNOWN

    details: dict[str, Any] | None = None

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        return ensure_utc_datetime(v)

    @field_validator("device_uid")
    @classmethod
    def validate_device_uid(cls, v: str) -> str:
        return strip_non_empty_str(v)
