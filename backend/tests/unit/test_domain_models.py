import uuid
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

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
from app.schemas.ai_analysis import AIAnalysisCreate
from app.schemas.alert import AlertCreate
from app.schemas.device import DeviceCreate
from app.schemas.elderly import ElderlyCreate, ElderlyResponse
from app.schemas.measurement import MeasurementCreate


def test_enums_values() -> None:
    assert DeviceStatus.ONLINE.value == "ONLINE"
    assert DeviceStatus.OFFLINE.value == "OFFLINE"
    assert DeviceStatus.UNKNOWN.value == "UNKNOWN"

    assert AlertType.FALL_SUSPECTED.value == "FALL_SUSPECTED"
    assert AlertType.HEART_RATE_ANOMALY.value == "HEART_RATE_ANOMALY"
    assert AlertType.SPO2_ANOMALY.value == "SPO2_ANOMALY"
    assert AlertType.TEMPERATURE_ANOMALY.value == "TEMPERATURE_ANOMALY"
    assert AlertType.SENSOR_HEALTH.value == "SENSOR_HEALTH"
    assert AlertType.DEVICE_OFFLINE.value == "DEVICE_OFFLINE"
    assert AlertType.GPS_UNAVAILABLE.value == "GPS_UNAVAILABLE"

    assert AlertSeverity.INFO.value == "INFO"
    assert AlertSeverity.CRITICAL.value == "CRITICAL"

    assert AlertStatus.OPEN.value == "OPEN"
    assert AlertStatus.ACKNOWLEDGED.value == "ACKNOWLEDGED"
    assert AlertStatus.RESOLVED.value == "RESOLVED"

    assert AlertSource.RULE_ENGINE.value == "RULE_ENGINE"
    assert AIProvider.NVIDIA.value == "NVIDIA"
    assert AIAnalysisStatus.PENDING.value == "PENDING"
    assert SensorHealthStatus.HEALTHY.value == "HEALTHY"


def test_elderly_schemas() -> None:
    create_dto = ElderlyCreate(
        first_name="Ahmed",
        last_name="Benali",
        date_of_birth=date(1948, 5, 12),
        phone="+213555123456",
        emergency_contact_name="Karim Benali",
        emergency_contact_phone="+213555654321",
    )
    assert create_dto.first_name == "Ahmed"
    assert create_dto.is_active is True

    now = datetime.now(UTC)
    uid = uuid.uuid4()
    response_dto = ElderlyResponse(
        id=uid,
        first_name="Ahmed",
        last_name="Benali",
        created_at=now,
        updated_at=now,
    )
    assert response_dto.id == uid
    assert response_dto.first_name == "Ahmed"


def test_device_schemas() -> None:
    elderly_id = uuid.uuid4()
    create_dto = DeviceCreate(
        device_uid="ESP32-DEV-001",
        name="Bracelet Ahmed",
        elderly_id=elderly_id,
        capabilities={"mpu6050": True, "max30102": True, "dht11": True, "gps": True},
    )
    assert create_dto.device_uid == "ESP32-DEV-001"
    assert create_dto.status == DeviceStatus.UNKNOWN
    assert create_dto.capabilities is not None and create_dto.capabilities["gps"] is True


def test_measurement_schemas_limits() -> None:
    now = datetime.now(UTC)
    dto = MeasurementCreate(
        device_id=uuid.uuid4(),
        elderly_id=uuid.uuid4(),
        measured_at=now,
        bpm=75.0,
        spo2=98.0,
        finger_detected=True,
        temperature_c=36.6,
        humidity_percent=45.0,
        accel_x_g=0.02,
        accel_y_g=0.01,
        accel_z_g=0.98,
        accel_magnitude_g=0.9805,
        gps_latitude=36.7525,
        gps_longitude=3.0422,
        gps_fix_valid=True,
    )
    assert dto.finger_detected is True
    assert dto.bpm == 75.0

    # SpO2 cannot be > 100
    with pytest.raises(ValidationError):
        MeasurementCreate(
            device_id=uuid.uuid4(),
            elderly_id=uuid.uuid4(),
            measured_at=now,
            spo2=150.0,
        )


def test_alert_and_ai_schemas() -> None:
    now = datetime.now(UTC)
    alert_dto = AlertCreate(
        elderly_id=uuid.uuid4(),
        alert_type=AlertType.FALL_SUSPECTED,
        severity=AlertSeverity.HIGH,
        title="Chute suspectée détectée",
        description="Forte accélération suivie d'une immobilité prolongée.",
        source=AlertSource.RULE_ENGINE,
        occurred_at=now,
        dedup_key="elderly_1:FALL_SUSPECTED",
    )
    assert alert_dto.occurrence_count == 1
    assert alert_dto.status == AlertStatus.OPEN

    ai_dto = AIAnalysisCreate(
        alert_id=uuid.uuid4(),
        provider=AIProvider.NVIDIA,
        status=AIAnalysisStatus.COMPLETED,
        risk_level="HIGH",
        anomaly_detected=True,
        possible_event="fall_suspected",
        explanation="Accélération de 3.2g suivie d'immobilité.",
        recommended_action="Contacter les secours ou l'aidant.",
        confidence=0.88,
        model_name="meta/llama-3.1-70b-instruct",
        latency_ms=340,
    )
    assert ai_dto.provider == AIProvider.NVIDIA
    assert ai_dto.confidence == 0.88
