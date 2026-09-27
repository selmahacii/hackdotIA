import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import DeviceStatus, SensorHealthStatus
from app.models.measurement import Measurement
from app.models.sensor_health import SensorHealth
from app.repositories.sensor_health import SensorHealthRepository
from app.services.processing import ProcessingService


@pytest.fixture
async def setup_pipeline_entities(
    db_session: AsyncSession,
) -> tuple[ElderlyPerson, Device]:
    elderly = ElderlyPerson(
        first_name="Jeanne",
        last_name="Moreau",
        phone="+33698765432",
        is_active=True,
    )
    db_session.add(elderly)
    await db_session.flush()

    device = Device(
        device_uid=f"ESP32-PIPE-{uuid.uuid4().hex[:8]}",
        name="Bracelet Jeanne",
        elderly_id=elderly.id,
        status=DeviceStatus.ONLINE,
    )
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return elderly, device


@pytest.mark.asyncio
async def test_processing_pipeline_healthy_persists_sensor_health(
    db_session: AsyncSession,
    setup_pipeline_entities: tuple[ElderlyPerson, Device],
) -> None:
    """
    Verifies that processing a healthy measurement creates a complete SensorHealth
    record linked to measurement and device with HEALTHY statuses and rich JSONB details.
    """
    elderly, device = setup_pipeline_entities
    now = datetime.now(UTC)

    measurement = Measurement(
        event_id=uuid.uuid4(),
        device_id=device.id,
        elderly_id=elderly.id,
        received_at=now,
        measured_at=now,
        finger_detected=True,
        bpm=74.0,
        spo2=99.0,
        temperature_c=21.5,
        humidity_percent=50.0,
        accel_x_g=0.02,
        accel_y_g=0.03,
        accel_z_g=0.98,
        accel_magnitude_g=0.981,
        gps_fix_valid=True,
        gps_latitude=48.8566,
        gps_longitude=2.3522,
        battery_level=88.0,
        wifi_rssi=-58,
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

    # Verify JSONB structured payload
    assert health.details is not None
    assert "battery" in health.details
    assert health.details["battery"]["status"] == "NORMAL"
    assert health.details["battery"]["level"] == 88.0
    assert "device" in health.details
    assert health.details["device"]["status"] == "ONLINE"
    assert "reasons" in health.details
    assert health.details["reasons"]["max30102"] is None
    assert health.details["reasons"]["dht11"] is None
    assert health.details["reasons"]["mpu6050"] is None
    assert health.details["reasons"]["gps"] is None

    # Query via repository to verify DB persistence
    repo = SensorHealthRepository(db_session)
    queried = await repo.get_by_measurement_id(measurement.id)
    assert queried is not None
    assert queried.id == health.id


@pytest.mark.asyncio
async def test_processing_pipeline_degraded_sensors(
    db_session: AsyncSession,
    setup_pipeline_entities: tuple[ElderlyPerson, Device],
) -> None:
    """
    Verifies sensor health evaluation when sensors report degraded/disconnected conditions:
    - MAX30102: no finger -> DISCONNECTED
    - GPS: no fix for > 180s -> DEGRADED
    - Battery: 15% -> WARNING
    """
    elderly, device = setup_pipeline_entities
    base_time = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)

    # Historical measurement with no GPS fix 4 minutes ago
    past_meas = Measurement(
        event_id=uuid.uuid4(),
        device_id=device.id,
        elderly_id=elderly.id,
        received_at=base_time - timedelta(seconds=240),
        measured_at=base_time - timedelta(seconds=240),
        finger_detected=True,
        bpm=70.0,
        spo2=98.0,
        temperature_c=22.0,
        humidity_percent=50.0,
        accel_x_g=0.0,
        accel_y_g=0.0,
        accel_z_g=1.0,
        gps_fix_valid=False,
        battery_level=18.0,
    )
    db_session.add(past_meas)
    await db_session.commit()

    # Current measurement: no finger, invalid GPS fix, low battery
    current_meas = Measurement(
        event_id=uuid.uuid4(),
        device_id=device.id,
        elderly_id=elderly.id,
        received_at=base_time,
        measured_at=base_time,
        finger_detected=False,
        bpm=None,
        spo2=None,
        temperature_c=22.0,
        humidity_percent=50.0,
        accel_x_g=0.0,
        accel_y_g=0.0,
        accel_z_g=1.0,
        gps_fix_valid=False,
        battery_level=15.0,
    )
    db_session.add(current_meas)
    await db_session.commit()
    await db_session.refresh(current_meas)

    service = ProcessingService(db_session)
    health = await service.process_measurement(current_meas, now=base_time)

    assert health is not None
    assert health.max30102_status == SensorHealthStatus.NO_CONTACT
    assert health.gps_status == SensorHealthStatus.UNAVAILABLE
    assert health.details is not None
    assert health.details["battery"]["status"] == "WARNING"


@pytest.mark.asyncio
async def test_processing_pipeline_idempotence(
    db_session: AsyncSession,
    setup_pipeline_entities: tuple[ElderlyPerson, Device],
) -> None:
    """
    Calling process_measurement twice on the same measurement must return
    the same SensorHealth row and not create duplicate rows in the DB.
    """
    elderly, device = setup_pipeline_entities
    now = datetime.now(UTC)

    measurement = Measurement(
        event_id=uuid.uuid4(),
        device_id=device.id,
        elderly_id=elderly.id,
        received_at=now,
        measured_at=now,
        finger_detected=True,
        bpm=80.0,
        spo2=97.0,
    )
    db_session.add(measurement)
    await db_session.commit()
    await db_session.refresh(measurement)

    service = ProcessingService(db_session)

    health1 = await service.process_measurement(measurement)
    health2 = await service.process_measurement(measurement)

    assert health1 is not None
    assert health2 is not None
    assert health1.id == health2.id

    # Verify DB table row count for this measurement
    stmt = select(func.count(SensorHealth.id)).where(SensorHealth.measurement_id == measurement.id)
    res = await db_session.execute(stmt)
    assert res.scalar_one() == 1
