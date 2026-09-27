import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import DeviceStatus, SensorHealthStatus
from app.models.measurement import Measurement
from app.models.sensor_health import SensorHealth
from app.services.processing import ProcessingService
from app.services.sensor_health import SensorHealthService


@pytest.fixture
async def setup_elderly_and_device(
    db_session: AsyncSession,
) -> tuple[ElderlyPerson, Device]:
    elderly = ElderlyPerson(
        first_name="Simone",
        last_name="Veil",
        phone="+33612345600",
        is_active=True,
    )
    db_session.add(elderly)
    await db_session.flush()

    device = Device(
        device_uid=f"ESP32-PROC-{uuid.uuid4().hex[:8]}",
        name="Bracelet Simone",
        elderly_id=elderly.id,
        status=DeviceStatus.ONLINE,
    )
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return elderly, device


@pytest.mark.asyncio
async def test_normal_processing_persists_sensor_health(
    db_session: AsyncSession,
    setup_elderly_and_device: tuple[ElderlyPerson, Device],
) -> None:
    elderly, device = setup_elderly_and_device
    now = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)

    # Persist a valid Measurement
    measurement = Measurement(
        event_id=uuid.uuid4(),
        device_id=device.id,
        elderly_id=elderly.id,
        received_at=now,
        measured_at=now,
        finger_detected=True,
        bpm=75.0,
        spo2=98.0,
        temperature_c=22.0,
        humidity_percent=48.0,
        accel_x_g=0.01,
        accel_y_g=0.01,
        accel_z_g=0.99,
        accel_magnitude_g=0.99,
        gps_fix_valid=True,
        gps_latitude=48.8566,
        gps_longitude=2.3522,
        battery_level=90.0,
        wifi_rssi=-60,
    )
    db_session.add(measurement)
    await db_session.commit()
    await db_session.refresh(measurement)

    service = ProcessingService(db_session)
    health = await service.process_measurement(measurement)

    assert health is not None
    assert health.id is not None
    assert health.measurement_id == measurement.id
    assert health.device_id == device.id
    assert health.max30102_status == SensorHealthStatus.HEALTHY
    assert health.dht11_status == SensorHealthStatus.HEALTHY
    assert health.mpu6050_status == SensorHealthStatus.HEALTHY
    assert health.gps_status == SensorHealthStatus.HEALTHY
    assert health.details is not None
    assert health.details["battery"]["status"] == "NORMAL"


@pytest.mark.asyncio
async def test_duplicate_processing_idempotence(
    db_session: AsyncSession,
    setup_elderly_and_device: tuple[ElderlyPerson, Device],
) -> None:
    elderly, device = setup_elderly_and_device
    now = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)

    measurement = Measurement(
        event_id=uuid.uuid4(),
        device_id=device.id,
        elderly_id=elderly.id,
        received_at=now,
        measured_at=now,
        finger_detected=False,
    )
    db_session.add(measurement)
    await db_session.commit()
    await db_session.refresh(measurement)

    service = ProcessingService(db_session)

    # First call
    health1 = await service.process_measurement(measurement)
    assert health1 is not None

    # Second call (duplicate processing)
    health2 = await service.process_measurement(measurement)
    assert health2 is not None

    # Must be the exact same SensorHealth instance/id
    assert health1.id == health2.id

    # Verify only ONE row exists in database for this measurement
    stmt = select(SensorHealth).where(SensorHealth.measurement_id == measurement.id)
    res = await db_session.execute(stmt)
    records = res.scalars().all()
    assert len(records) == 1


@pytest.mark.asyncio
async def test_sensor_health_failure_does_not_delete_measurement(
    db_session: AsyncSession,
    setup_elderly_and_device: tuple[ElderlyPerson, Device],
) -> None:
    elderly, device = setup_elderly_and_device
    now = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)

    measurement = Measurement(
        event_id=uuid.uuid4(),
        device_id=device.id,
        elderly_id=elderly.id,
        received_at=now,
        measured_at=now,
        finger_detected=True,
        bpm=70.0,
    )
    db_session.add(measurement)
    await db_session.commit()
    await db_session.refresh(measurement)

    # Mock SensorHealthService to raise an unexpected runtime error
    mock_sensor_service = MagicMock(spec=SensorHealthService)
    mock_sensor_service.evaluate.side_effect = RuntimeError("Simulated internal algorithm failure")

    service = ProcessingService(db_session, sensor_health_service=mock_sensor_service)
    meas_id = measurement.id
    result = await service.process_measurement(measurement)

    # Processing fails gracefully and returns None
    assert result is None

    # CRITICAL: Measurement must remain completely intact in PostgreSQL!
    meas_stmt = select(Measurement).where(Measurement.id == meas_id)
    meas_res = await db_session.execute(meas_stmt)
    persisted_meas = meas_res.scalars().first()
    assert persisted_meas is not None
    assert persisted_meas.id == meas_id
    assert persisted_meas.bpm == 70.0
