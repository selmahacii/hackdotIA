import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analysis import AIAnalysis
from app.models.alert import Alert
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import (
    AIAnalysisStatus,
    AIProvider,
    AlertSeverity,
    AlertSource,
    AlertStatus,
    AlertType,
    DeviceStatus,
    SensorHealthStatus,
)
from app.models.measurement import Measurement
from app.models.sensor_health import SensorHealth
from app.repositories.alert import AlertRepository
from app.repositories.device import DeviceRepository
from app.repositories.elderly import ElderlyRepository
from app.repositories.measurement import MeasurementRepository


@pytest.mark.asyncio
async def test_full_domain_chain_insertion(db_session: AsyncSession) -> None:
    now = datetime.now(UTC)

    # 1. ElderlyPerson
    elderly = ElderlyPerson(
        first_name="Fatima",
        last_name="Zahra",
        date_of_birth=date(1942, 3, 15),
        phone="+213555987654",
        emergency_contact_name="Amina Zahra",
        emergency_contact_phone="+213555112233",
        is_active=True,
    )
    db_session.add(elderly)
    await db_session.flush()
    assert elderly.id is not None
    assert isinstance(elderly.id, uuid.UUID)

    # 2. Device
    device = Device(
        device_uid=f"ESP32-TEST-{uuid.uuid4().hex[:6]}",
        name="Bracelet Fatima",
        elderly_id=elderly.id,
        status=DeviceStatus.ONLINE,
        firmware_version="1.0.0",
        capabilities={"mpu6050": True, "max30102": True, "dht11": True, "gps": True},
    )
    db_session.add(device)
    await db_session.flush()
    assert device.id is not None

    # 3. Measurement
    measurement = Measurement(
        device_id=device.id,
        elderly_id=elderly.id,
        measured_at=now,
        bpm=76.0,
        spo2=98.0,
        finger_detected=True,
        temperature_c=36.7,
        humidity_percent=50.0,
        accel_x_g=0.01,
        accel_y_g=0.02,
        accel_z_g=0.99,
        accel_magnitude_g=0.9902,
        gps_latitude=36.75,
        gps_longitude=3.05,
        gps_fix_valid=True,
    )
    db_session.add(measurement)
    await db_session.flush()
    assert measurement.id is not None

    # 4. SensorHealth
    sensor_health = SensorHealth(
        measurement_id=measurement.id,
        device_id=device.id,
        max30102_status=SensorHealthStatus.HEALTHY,
        dht11_status=SensorHealthStatus.HEALTHY,
        mpu6050_status=SensorHealthStatus.HEALTHY,
        gps_status=SensorHealthStatus.HEALTHY,
        details={"self_test": "passed"},
    )
    db_session.add(sensor_health)
    await db_session.flush()
    assert sensor_health.id is not None

    # 5. Alert
    alert = Alert(
        elderly_id=elderly.id,
        device_id=device.id,
        alert_type=AlertType.FALL_SUSPECTED,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        title="Chute suspectée",
        description="Pic d'accélération détecté sur le poignet.",
        source=AlertSource.RULE_ENGINE,
        occurred_at=now,
        dedup_key=f"{elderly.id}:FALL_SUSPECTED",
        occurrence_count=1,
    )
    db_session.add(alert)
    await db_session.flush()
    assert alert.id is not None

    # 6. AIAnalysis
    ai_analysis = AIAnalysis(
        alert_id=alert.id,
        provider=AIProvider.NVIDIA,
        status=AIAnalysisStatus.COMPLETED,
        risk_level="HIGH",
        anomaly_detected=True,
        possible_event="fall_suspected",
        explanation="Accélération supérieure au seuil critique suivie d'immobilité.",
        recommended_action="Prendre contact immédiat avec le résident.",
        confidence=0.92,
        model_name="meta/llama-3.1-70b-instruct",
        latency_ms=280,
    )
    db_session.add(ai_analysis)
    await db_session.flush()
    assert ai_analysis.id is not None

    # Verify query
    stmt = select(ElderlyPerson).where(ElderlyPerson.id == elderly.id)
    result = await db_session.execute(stmt)
    loaded_elderly = result.scalar_one()
    assert loaded_elderly.first_name == "Fatima"


@pytest.mark.asyncio
async def test_measurement_real_sensor_cases(db_session: AsyncSession) -> None:
    now = datetime.now(UTC)

    # Setup elderly and device
    elderly = ElderlyPerson(first_name="Test", last_name="Cases")
    db_session.add(elderly)
    await db_session.flush()

    device = Device(
        device_uid=f"ESP32-CASES-{uuid.uuid4().hex[:6]}",
        elderly_id=elderly.id,
    )
    db_session.add(device)
    await db_session.flush()

    # Cas 1: finger_detected = false, bpm = NULL, spo2 = NULL (doit être accepté)
    m1 = Measurement(
        device_id=device.id,
        elderly_id=elderly.id,
        measured_at=now,
        finger_detected=False,
        bpm=None,
        spo2=None,
    )
    db_session.add(m1)
    await db_session.flush()
    assert m1.id is not None
    assert m1.bpm is None
    assert m1.spo2 is None
    assert m1.finger_detected is False

    # Cas 2: gps_fix_valid = false, gps_latitude = NULL, gps_longitude = NULL (doit être accepté)
    m2 = Measurement(
        device_id=device.id,
        elderly_id=elderly.id,
        measured_at=now,
        gps_fix_valid=False,
        gps_latitude=None,
        gps_longitude=None,
    )
    db_session.add(m2)
    await db_session.flush()
    assert m2.id is not None
    assert m2.gps_latitude is None
    assert m2.gps_longitude is None
    assert m2.gps_fix_valid is False

    # Cas 3: gps_fix_valid = true, gps_latitude = 36.75, gps_longitude = 3.05 (doit être accepté)
    m3 = Measurement(
        device_id=device.id,
        elderly_id=elderly.id,
        measured_at=now,
        gps_fix_valid=True,
        gps_latitude=36.75,
        gps_longitude=3.05,
    )
    db_session.add(m3)
    await db_session.flush()
    assert m3.id is not None
    assert m3.gps_latitude == 36.75
    assert m3.gps_longitude == 3.05
    assert m3.gps_fix_valid is True

    # Cas 4: finger_detected = true, bpm = 78, spo2 = 97 (doit être accepté)
    m4 = Measurement(
        device_id=device.id,
        elderly_id=elderly.id,
        measured_at=now,
        finger_detected=True,
        bpm=78.0,
        spo2=97.0,
    )
    db_session.add(m4)
    await db_session.flush()
    assert m4.id is not None
    assert m4.bpm == 78.0
    assert m4.spo2 == 97.0


@pytest.mark.asyncio
async def test_repositories(db_session: AsyncSession) -> None:
    elderly_repo = ElderlyRepository(db_session)
    device_repo = DeviceRepository(db_session)
    alert_repo = AlertRepository(db_session)
    measurement_repo = MeasurementRepository(db_session)

    elderly = await elderly_repo.create(
        ElderlyPerson(first_name="Repo", last_name="User", is_active=True)
    )
    active_elderly = await elderly_repo.list_active()
    assert any(e.id == elderly.id for e in active_elderly)

    uid_str = f"UID-{uuid.uuid4().hex[:6]}"
    device = await device_repo.create(
        Device(device_uid=uid_str, elderly_id=elderly.id, status=DeviceStatus.ONLINE)
    )
    found_device = await device_repo.get_by_uid(uid_str)
    assert found_device is not None
    assert found_device.id == device.id

    now = datetime.now(UTC)
    measurement = await measurement_repo.create(
        Measurement(
            device_id=device.id,
            elderly_id=elderly.id,
            measured_at=now,
            bpm=80.0,
        )
    )
    measurements = await measurement_repo.list_recent_by_device(device.id)
    assert len(measurements) >= 1
    assert measurements[0].id == measurement.id

    dedup = f"{elderly.id}:TEST_ALERT"
    alert = await alert_repo.create(
        Alert(
            elderly_id=elderly.id,
            alert_type=AlertType.HEART_RATE_ANOMALY,
            severity=AlertSeverity.MEDIUM,
            status=AlertStatus.OPEN,
            title="Rythme cardiaque anormal",
            description="Fréquence mesurée au-dessus du seuil",
            source=AlertSource.RULE_ENGINE,
            occurred_at=now,
            dedup_key=dedup,
        )
    )
    active_alert = await alert_repo.get_active_by_dedup_key(dedup)
    assert active_alert is not None
    assert active_alert.id == alert.id
