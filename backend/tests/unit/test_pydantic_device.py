from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.enums import DeviceStatus, SensorHealthStatus
from app.schemas.telemetry import DeviceStatusPayload, SensorHealthPayload


def test_device_status_payload_valid() -> None:
    now = datetime.now(UTC)
    payload = DeviceStatusPayload(
        schema_version="1.0",
        device_uid="ESP32-ELDERLY-001",
        timestamp=now,
        status=DeviceStatus.ONLINE,
        battery_level=90,
        wifi_rssi=-62,
        firmware_version="1.0.2",
    )
    assert payload.device_uid == "ESP32-ELDERLY-001"
    assert payload.status == DeviceStatus.ONLINE
    assert payload.battery_level == 90


def test_device_uid_cannot_be_empty_or_spaces() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        DeviceStatusPayload(
            device_uid="",
            timestamp=now,
            status=DeviceStatus.ONLINE,
        )
    with pytest.raises(ValidationError):
        DeviceStatusPayload(
            device_uid="   ",
            timestamp=now,
            status=DeviceStatus.ONLINE,
        )


def test_device_status_extra_forbidden() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        DeviceStatusPayload.model_validate(
            {
                "device_uid": "ESP32-001",
                "timestamp": now,
                "status": DeviceStatus.ONLINE,
                "unexpected_field": "injection",
            }
        )


def test_sensor_health_payload_valid() -> None:
    now = datetime.now(UTC)
    payload = SensorHealthPayload(
        device_uid="ESP32-ELDERLY-001",
        timestamp=now,
        max30102_status=SensorHealthStatus.HEALTHY,
        dht11_status=SensorHealthStatus.HEALTHY,
        mpu6050_status=SensorHealthStatus.HEALTHY,
        gps_status=SensorHealthStatus.NO_CONTACT,
        details={"gps_satellite_count": 0},
    )
    assert payload.max30102_status == SensorHealthStatus.HEALTHY
    assert payload.gps_status == SensorHealthStatus.NO_CONTACT
    assert payload.details == {"gps_satellite_count": 0}
