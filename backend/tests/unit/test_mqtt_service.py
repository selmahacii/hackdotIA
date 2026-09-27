import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import DeviceStatus, SensorHealthStatus
from app.mqtt.errors import (
    DuplicateEventError,
    InvalidPayloadError,
    TopicMismatchError,
    UnknownDeviceError,
)
from app.mqtt.service import MQTTIngestionService


@pytest.fixture
async def sample_elderly_and_device(
    db_session: AsyncSession,
) -> tuple[ElderlyPerson, Device]:
    elderly = ElderlyPerson(
        first_name="Jean",
        last_name="Dupont",
        phone="+33612345678",
        is_active=True,
    )
    db_session.add(elderly)
    await db_session.flush()

    device = Device(
        device_uid=f"ESP32-UNIT-{uuid.uuid4().hex[:8]}",
        name="Bracelet Jean",
        elderly_id=elderly.id,
        status=DeviceStatus.UNKNOWN,
    )
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return elderly, device


@pytest.mark.asyncio
async def test_telemetry_successful_ingestion(
    db_session: AsyncSession,
    sample_elderly_and_device: tuple[ElderlyPerson, Device],
) -> None:
    _, device = sample_elderly_and_device
    service = MQTTIngestionService(db_session)

    event_id = uuid.uuid4()
    payload = {
        "schema_version": "1.0",
        "event_id": str(event_id),
        "device_uid": device.device_uid,
        "timestamp": "2026-09-27T10:30:00Z",
        "finger_detected": True,
        "bpm": 74.0,
        "spo2": 98.0,
        "temperature_c": 22.5,
        "humidity_percent": 45.0,
        "accel_x_g": 0.02,
        "accel_y_g": 0.01,
        "accel_z_g": 0.99,
        "accel_magnitude_g": 0.99,
        "gps_fix_valid": True,
        "gps_latitude": 48.8566,
        "gps_longitude": 2.3522,
        "battery_level": 88,
        "wifi_rssi": -60,
    }

    measurement = await service.ingest_telemetry(payload, topic_device_uid=device.device_uid)

    assert measurement.id is not None
    assert measurement.event_id == event_id
    assert measurement.device_id == device.id
    assert measurement.bpm == 74.0
    assert measurement.battery_level == 88.0
    assert measurement.measured_at == datetime(2026, 9, 27, 10, 30, tzinfo=UTC)

    # Check device was updated
    await db_session.refresh(device)
    assert device.status == DeviceStatus.ONLINE
    assert device.last_seen_at is not None
    assert device.battery_level == 88.0
    assert device.wifi_rssi == -60


@pytest.mark.asyncio
async def test_telemetry_unknown_device_rejected(db_session: AsyncSession) -> None:
    service = MQTTIngestionService(db_session)
    payload = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "device_uid": "ESP32-NONEXISTENT",
        "timestamp": "2026-09-27T10:30:00Z",
        "finger_detected": False,
    }

    with pytest.raises(UnknownDeviceError) as exc_info:
        await service.ingest_telemetry(payload, topic_device_uid="ESP32-NONEXISTENT")
    assert "ESP32-NONEXISTENT" in str(exc_info.value)


@pytest.mark.asyncio
async def test_telemetry_topic_mismatch_rejected(
    db_session: AsyncSession,
    sample_elderly_and_device: tuple[ElderlyPerson, Device],
) -> None:
    _, device = sample_elderly_and_device
    service = MQTTIngestionService(db_session)
    payload = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "device_uid": device.device_uid,
        "timestamp": "2026-09-27T10:30:00Z",
        "finger_detected": False,
    }

    with pytest.raises(TopicMismatchError) as exc_info:
        await service.ingest_telemetry(payload, topic_device_uid="ESP32-SPOOFED")
    assert "ESP32-SPOOFED" in str(exc_info.value)


@pytest.mark.asyncio
async def test_telemetry_invalid_payload_rejected(
    db_session: AsyncSession,
    sample_elderly_and_device: tuple[ElderlyPerson, Device],
) -> None:
    _, device = sample_elderly_and_device
    service = MQTTIngestionService(db_session)

    # Invalid cross-field rule: finger_detected=False but bpm is provided
    payload = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "device_uid": device.device_uid,
        "timestamp": "2026-09-27T10:30:00Z",
        "finger_detected": False,
        "bpm": 80.0,
    }

    with pytest.raises(InvalidPayloadError):
        await service.ingest_telemetry(payload, topic_device_uid=device.device_uid)


@pytest.mark.asyncio
async def test_telemetry_idempotence_duplicate_rejected(
    db_session: AsyncSession,
    sample_elderly_and_device: tuple[ElderlyPerson, Device],
) -> None:
    _, device = sample_elderly_and_device
    service = MQTTIngestionService(db_session)

    event_id = uuid.uuid4()
    payload = {
        "schema_version": "1.0",
        "event_id": str(event_id),
        "device_uid": device.device_uid,
        "timestamp": "2026-09-27T10:30:00Z",
        "finger_detected": False,
    }

    # First attempt succeeds
    m1 = await service.ingest_telemetry(payload, topic_device_uid=device.device_uid)
    assert m1.event_id == event_id

    # Second attempt with same event_id fails cleanly with DuplicateEventError
    with pytest.raises(DuplicateEventError) as exc_info:
        await service.ingest_telemetry(payload, topic_device_uid=device.device_uid)
    assert str(event_id) in str(exc_info.value)


@pytest.mark.asyncio
async def test_device_status_ingestion(
    db_session: AsyncSession,
    sample_elderly_and_device: tuple[ElderlyPerson, Device],
) -> None:
    _, device = sample_elderly_and_device
    service = MQTTIngestionService(db_session)

    payload = {
        "schema_version": "1.0",
        "device_uid": device.device_uid,
        "timestamp": "2026-09-27T10:45:00Z",
        "status": "ONLINE",
        "battery_level": 92,
        "wifi_rssi": -55,
        "firmware_version": "v1.2.3",
    }

    updated_device = await service.ingest_status(payload, topic_device_uid=device.device_uid)
    assert updated_device.status == DeviceStatus.ONLINE
    assert updated_device.battery_level == 92.0
    assert updated_device.firmware_version == "v1.2.3"
    assert updated_device.wifi_rssi == -55

    # Verify no measurement was created
    measurements = await service.measurement_repo.list_recent_by_device(device.id)
    assert len(measurements) == 0


@pytest.mark.asyncio
async def test_sensor_health_ingestion(
    db_session: AsyncSession,
    sample_elderly_and_device: tuple[ElderlyPerson, Device],
) -> None:
    _, device = sample_elderly_and_device
    service = MQTTIngestionService(db_session)

    payload = {
        "schema_version": "1.0",
        "device_uid": device.device_uid,
        "timestamp": "2026-09-27T10:50:00Z",
        "max30102_status": "HEALTHY",
        "dht11_status": "HEALTHY",
        "mpu6050_status": "HEALTHY",
        "gps_status": "NO_CONTACT",
        "details": {"i2c_bus": "ok"},
    }

    health = await service.ingest_health(payload, topic_device_uid=device.device_uid)
    assert health.id is not None
    assert health.measurement_id is None
    assert health.max30102_status == SensorHealthStatus.HEALTHY
    assert health.gps_status == SensorHealthStatus.NO_CONTACT
    assert health.details == {"i2c_bus": "ok"}
