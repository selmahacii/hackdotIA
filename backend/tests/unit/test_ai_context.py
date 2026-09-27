"""Unit tests for AI Context Builder and prompt generation."""

import uuid
from datetime import UTC, datetime

from app.models.alert import Alert
from app.models.enums import AlertSeverity, AlertSource, AlertStatus, AlertType, SensorHealthStatus
from app.models.measurement import Measurement
from app.models.sensor_health import SensorHealth
from app.services.ai_context import SYSTEM_PROMPT, AIContextBuilder


def test_system_prompt_compliance_rules() -> None:
    assert "ABSOLUTELY NO MEDICAL DIAGNOSES" in SYSTEM_PROMPT
    assert "OBJECTIVE SENSOR ANALYSIS ONLY" in SYSTEM_PROMPT
    assert "REQUIRED JSON OUTPUT SCHEMA" in SYSTEM_PROMPT


def test_build_context_dto_data_minimization() -> None:
    builder = AIContextBuilder()
    alert_id = uuid.uuid4()
    device_id = uuid.uuid4()
    elderly_id = uuid.uuid4()
    measurement_id = uuid.uuid4()

    alert = Alert(
        id=alert_id,
        elderly_id=elderly_id,
        device_id=device_id,
        alert_type=AlertType.FALL_SUSPECTED,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.OPEN,
        title="Fall Suspected Alert",
        description="Sudden acceleration spike detected",
        source=AlertSource.RULE_ENGINE,
        dedup_key="fall:test",
        context={"measurement_id": str(measurement_id)},
        created_at=datetime.now(UTC),
    )

    measurement = Measurement(
        id=measurement_id,
        device_id=device_id,
        elderly_id=elderly_id,
        bpm=110.0,
        spo2=96.0,
        temperature_c=36.8,
        accel_magnitude_g=3.4,
        finger_detected=True,
        gps_fix_valid=True,
        battery_level=85.0,
        wifi_rssi=-65,
        measured_at=datetime.now(UTC),
    )

    sensor_health = SensorHealth(
        measurement_id=measurement_id,
        device_id=device_id,
        mpu6050_status=SensorHealthStatus.HEALTHY,
        max30102_status=SensorHealthStatus.HEALTHY,
        dht11_status=SensorHealthStatus.HEALTHY,
        gps_status=SensorHealthStatus.HEALTHY,
        details={"status": "all sensors normal"},
        checked_at=datetime.now(UTC),
    )

    dto = builder.build_context_dto(
        alert=alert,
        measurement=measurement,
        sensor_health=sensor_health,
        recent_measurements=[measurement],
    )

    # Validate DTO contains technical metrics but NO personal PII
    assert dto.alert_id == alert_id
    assert dto.alert_type == "FALL_SUSPECTED"
    assert dto.severity == "CRITICAL"
    assert dto.triggering_measurement is not None
    assert dto.triggering_measurement["bpm"] == 110.0
    assert dto.triggering_measurement["accel_magnitude_g"] == 3.4
    assert dto.sensor_health is not None
    assert dto.sensor_health["mpu6050_status"] == "HEALTHY"
    assert len(dto.recent_measurements) == 1

    # Verify prompts
    sys_prompt, user_prompt = builder.build_prompts(dto)
    assert sys_prompt == SYSTEM_PROMPT
    assert "ALERT TYPE: FALL_SUSPECTED" in user_prompt
    assert "SEVERITY: CRITICAL" in user_prompt
    assert "accel_magnitude_g: 3.4" in user_prompt


def test_deterministic_fallback_generation() -> None:
    builder = AIContextBuilder()

    fallback_fall = builder.create_fallback_enrichment("FALL_SUSPECTED", "CRITICAL")
    assert "fall" in fallback_fall.summary.lower()
    assert fallback_fall.confidence == 0.70
    assert len(fallback_fall.recommended_checks) > 0
    assert any(
        "consciousness" in check.lower() or "physical" in check.lower()
        for check in fallback_fall.recommended_checks
    )

    fallback_heart = builder.create_fallback_enrichment("HEART_RATE_ANOMALY", "HIGH")
    assert "heart rate" in fallback_heart.summary.lower()
    assert fallback_heart.confidence == 0.70

    fallback_temp = builder.create_fallback_enrichment("TEMPERATURE_ANOMALY", "MEDIUM")
    assert "temperature" in fallback_temp.summary.lower()
