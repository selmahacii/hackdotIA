import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.telemetry import SensorTelemetryPayload


def test_payload_1_nominal() -> None:
    """1. Telemetry nominale: all sensors valid and healthy."""
    data = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "device_uid": "ESP32-VALID-001",
        "timestamp": datetime.now(UTC).isoformat(),
        "finger_detected": True,
        "bpm": 72.0,
        "spo2": 98.0,
        "temperature_c": 22.5,
        "humidity_percent": 45.0,
        "accel_x_g": 0.01,
        "accel_y_g": 0.02,
        "accel_z_g": 0.98,
        "accel_magnitude_g": 0.981,
        "gps_fix_valid": True,
        "gps_latitude": 48.8566,
        "gps_longitude": 2.3522,
        "battery_level": 85,
        "wifi_rssi": -65,
    }
    payload = SensorTelemetryPayload.model_validate(data)
    assert payload.bpm == 72.0
    assert payload.spo2 == 98.0
    assert payload.finger_detected is True
    assert payload.temperature_c == 22.5
    assert payload.gps_fix_valid is True


def test_payload_2_finger_absent() -> None:
    """2. Finger absent: finger_detected=False, bpm=null, spo2=null."""
    data = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "device_uid": "ESP32-VALID-001",
        "timestamp": datetime.now(UTC).isoformat(),
        "finger_detected": False,
        "bpm": None,
        "spo2": None,
    }
    payload = SensorTelemetryPayload.model_validate(data)
    assert payload.finger_detected is False
    assert payload.bpm is None
    assert payload.spo2 is None

    # Invalid: finger_detected is False but BPM is non-null
    invalid_data = {**data, "bpm": 70.0}
    with pytest.raises(
        ValidationError, match="bpm and spo2 must be null when finger_detected is false"
    ):
        SensorTelemetryPayload.model_validate(invalid_data)


def test_payload_3_gps_no_fix() -> None:
    """3. GPS sans fix: gps_fix_valid=False, coordinates must be null."""
    data = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "device_uid": "ESP32-VALID-001",
        "timestamp": datetime.now(UTC).isoformat(),
        "gps_fix_valid": False,
        "gps_latitude": None,
        "gps_longitude": None,
    }
    payload = SensorTelemetryPayload.model_validate(data)
    assert payload.gps_fix_valid is False
    assert payload.gps_latitude is None
    assert payload.gps_longitude is None

    # Invalid: gps_fix_valid is False but latitude sent as 0.0 (Null Island error)
    invalid_data = {**data, "gps_latitude": 0.0, "gps_longitude": 0.0}
    with pytest.raises(
        ValidationError,
        match="gps_latitude and gps_longitude must be null when gps_fix_valid is false",
    ):
        SensorTelemetryPayload.model_validate(invalid_data)


def test_payload_4_gps_valid() -> None:
    """4. GPS valide: valid fix with bounded latitude and longitude."""
    data = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "device_uid": "ESP32-VALID-001",
        "timestamp": datetime.now(UTC).isoformat(),
        "gps_fix_valid": True,
        "gps_latitude": 48.8566,
        "gps_longitude": 2.3522,
    }
    payload = SensorTelemetryPayload.model_validate(data)
    assert payload.gps_fix_valid is True
    assert payload.gps_latitude == 48.8566
    assert payload.gps_longitude == 2.3522


def test_payload_5_temperature_valid() -> None:
    """5. Température et humidité valides (-40°C à 80°C, 0% à 100%)."""
    data = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "device_uid": "ESP32-VALID-001",
        "timestamp": datetime.now(UTC).isoformat(),
        "temperature_c": 19.8,
        "humidity_percent": 52.0,
    }
    payload = SensorTelemetryPayload.model_validate(data)
    assert payload.temperature_c == 19.8
    assert payload.humidity_percent == 52.0


def test_payload_6_temperature_out_of_bounds() -> None:
    """6. Température hors plage: rejeté par validation Pydantic."""
    base_data = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "device_uid": "ESP32-VALID-001",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    # Too hot (> 80.0°C)
    with pytest.raises(ValidationError):
        SensorTelemetryPayload.model_validate({**base_data, "temperature_c": 85.0})

    # Too cold (< -40.0°C)
    with pytest.raises(ValidationError):
        SensorTelemetryPayload.model_validate({**base_data, "temperature_c": -45.0})

    # Humidity out of range (> 100%)
    with pytest.raises(ValidationError):
        SensorTelemetryPayload.model_validate({**base_data, "humidity_percent": 105.0})


def test_payload_7_mpu_normal() -> None:
    """7. MPU normal (au repos, ~1g sur l'axe Z)."""
    data = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "device_uid": "ESP32-VALID-001",
        "timestamp": datetime.now(UTC).isoformat(),
        "accel_x_g": 0.02,
        "accel_y_g": 0.01,
        "accel_z_g": 0.99,
        "accel_magnitude_g": 0.991,
    }
    payload = SensorTelemetryPayload.model_validate(data)
    assert payload.accel_z_g == 0.99
    assert payload.accel_magnitude_g == 0.991


def test_payload_8_mpu_acceleration_spike() -> None:
    """8. MPU pic d'accélération (impact > 2.8g dans la limite matérielle +-8g)."""
    data = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "device_uid": "ESP32-VALID-001",
        "timestamp": datetime.now(UTC).isoformat(),
        "accel_x_g": 1.8,
        "accel_y_g": 1.5,
        "accel_z_g": 2.2,
        "accel_magnitude_g": 3.21,
    }
    payload = SensorTelemetryPayload.model_validate(data)
    assert payload.accel_magnitude_g == 3.21

    # Out of sensor physical range (> 8g on axis)
    with pytest.raises(ValidationError):
        SensorTelemetryPayload.model_validate({**data, "accel_x_g": 12.0})


def test_payload_9_battery_level() -> None:
    """9. Batterie faible (12%) acceptée, bornes [0, 100]."""
    data = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "device_uid": "ESP32-VALID-001",
        "timestamp": datetime.now(UTC).isoformat(),
        "battery_level": 12,
    }
    payload = SensorTelemetryPayload.model_validate(data)
    assert payload.battery_level == 12

    # Negative battery
    with pytest.raises(ValidationError):
        SensorTelemetryPayload.model_validate({**data, "battery_level": -5})

    # Above 100%
    with pytest.raises(ValidationError):
        SensorTelemetryPayload.model_validate({**data, "battery_level": 105})


def test_payload_10_wifi_rssi() -> None:
    """10. Wi-Fi RSSI faible (-88 dBm) accepté, bornes [-120, 0]."""
    data = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "device_uid": "ESP32-VALID-001",
        "timestamp": datetime.now(UTC).isoformat(),
        "wifi_rssi": -88,
    }
    payload = SensorTelemetryPayload.model_validate(data)
    assert payload.wifi_rssi == -88

    # Positive RSSI invalid
    with pytest.raises(ValidationError):
        SensorTelemetryPayload.model_validate({**data, "wifi_rssi": 10})


def test_legacy_field_names_rejected_by_extra_forbid() -> None:
    """Verification that non-suffixed keys from initial prompt are strictly rejected."""
    base = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "device_uid": "ESP32-VALID-001",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    # "temperature" instead of "temperature_c"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        SensorTelemetryPayload.model_validate({**base, "temperature": 22.0})

    # "accel_x" instead of "accel_x_g"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        SensorTelemetryPayload.model_validate({**base, "accel_x": 0.05})
