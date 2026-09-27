import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.schemas.telemetry import SensorTelemetryPayload


def make_valid_payload(**overrides: object) -> dict:
    payload = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "device_uid": "ESP32-ELDERLY-001",
        "timestamp": datetime.now(UTC).isoformat(),
        "bpm": 78.0,
        "spo2": 97.0,
        "finger_detected": True,
        "temperature_c": 23.4,
        "humidity_percent": 51.2,
        "accel_x_g": 0.02,
        "accel_y_g": 0.98,
        "accel_z_g": 0.11,
        "gps_latitude": 36.7525,
        "gps_longitude": 3.0420,
        "gps_fix_valid": True,
        "battery_level": 87,
        "wifi_rssi": -54,
    }
    payload.update(overrides)
    return payload


def test_max30102_validation_rules() -> None:
    # 1. finger=false + bpm=null + spo2=null -> PASS
    data1 = make_valid_payload(finger_detected=False, bpm=None, spo2=None)
    p1 = SensorTelemetryPayload(**data1)
    assert p1.finger_detected is False
    assert p1.bpm is None
    assert p1.spo2 is None

    # 2. finger=true + bpm=78 + spo2=97 -> PASS
    data2 = make_valid_payload(finger_detected=True, bpm=78.0, spo2=97.0)
    p2 = SensorTelemetryPayload(**data2)
    assert p2.finger_detected is True
    assert p2.bpm == 78.0
    assert p2.spo2 == 97.0

    # 3. finger=false + bpm=78 -> FAIL
    data3 = make_valid_payload(finger_detected=False, bpm=78.0, spo2=None)
    with pytest.raises(ValidationError) as exc:
        SensorTelemetryPayload(**data3)
    assert "bpm and spo2 must be null when finger_detected is false" in str(exc.value)

    # 4. spo2=101 -> FAIL
    data4 = make_valid_payload(spo2=101.0)
    with pytest.raises(ValidationError):
        SensorTelemetryPayload(**data4)

    # 5. bpm=251 -> FAIL
    data5 = make_valid_payload(bpm=251.0)
    with pytest.raises(ValidationError):
        SensorTelemetryPayload(**data5)


def test_dht11_validation_rules() -> None:
    # 1. temperature=23.4 -> PASS
    data1 = make_valid_payload(temperature_c=23.4)
    p1 = SensorTelemetryPayload(**data1)
    assert p1.temperature_c == 23.4

    # 2. humidity=51 -> PASS
    data2 = make_valid_payload(humidity_percent=51.0)
    p2 = SensorTelemetryPayload(**data2)
    assert p2.humidity_percent == 51.0

    # 3. humidity=101 -> FAIL
    data3 = make_valid_payload(humidity_percent=101.0)
    with pytest.raises(ValidationError):
        SensorTelemetryPayload(**data3)

    # 4. temperature below -40 or above 80 -> FAIL
    with pytest.raises(ValidationError):
        SensorTelemetryPayload(**make_valid_payload(temperature_c=-45.0))
    with pytest.raises(ValidationError):
        SensorTelemetryPayload(**make_valid_payload(temperature_c=85.0))


def test_mpu6050_validation_rules() -> None:
    # 1. 0.1, 0.2, 0.9 -> PASS
    data1 = make_valid_payload(accel_x_g=0.1, accel_y_g=0.2, accel_z_g=0.9)
    p1 = SensorTelemetryPayload(**data1)
    assert p1.accel_x_g == 0.1

    # 2. 8.1 -> FAIL
    data2 = make_valid_payload(accel_x_g=8.1)
    with pytest.raises(ValidationError):
        SensorTelemetryPayload(**data2)

    # 3. -8.1 -> FAIL
    data3 = make_valid_payload(accel_y_g=-8.1)
    with pytest.raises(ValidationError):
        SensorTelemetryPayload(**data3)


def test_gps_validation_rules() -> None:
    # 1. valid + coordinates -> PASS
    data1 = make_valid_payload(gps_fix_valid=True, gps_latitude=36.75, gps_longitude=3.05)
    p1 = SensorTelemetryPayload(**data1)
    assert p1.gps_fix_valid is True
    assert p1.gps_latitude == 36.75
    assert p1.gps_longitude == 3.05

    # 2. invalid + null coordinates -> PASS
    data2 = make_valid_payload(gps_fix_valid=False, gps_latitude=None, gps_longitude=None)
    p2 = SensorTelemetryPayload(**data2)
    assert p2.gps_fix_valid is False
    assert p2.gps_latitude is None
    assert p2.gps_longitude is None

    # 3. invalid + coordinates -> FAIL
    data3 = make_valid_payload(gps_fix_valid=False, gps_latitude=36.75, gps_longitude=None)
    with pytest.raises(ValidationError) as exc:
        SensorTelemetryPayload(**data3)
    assert "gps_latitude and gps_longitude must be null when gps_fix_valid is false" in str(
        exc.value
    )

    # 4. latitude=91 -> FAIL
    with pytest.raises(ValidationError):
        SensorTelemetryPayload(**make_valid_payload(gps_latitude=91.0))

    # 5. longitude=181 -> FAIL
    with pytest.raises(ValidationError):
        SensorTelemetryPayload(**make_valid_payload(gps_longitude=181.0))


def test_battery_and_wifi_validation_rules() -> None:
    # 1. battery=0 -> PASS
    p1 = SensorTelemetryPayload(**make_valid_payload(battery_level=0))
    assert p1.battery_level == 0

    # 2. battery=100 -> PASS
    p2 = SensorTelemetryPayload(**make_valid_payload(battery_level=100))
    assert p2.battery_level == 100

    # 3. battery=101 -> FAIL
    with pytest.raises(ValidationError):
        SensorTelemetryPayload(**make_valid_payload(battery_level=101))

    # 4. battery=-1 -> FAIL
    with pytest.raises(ValidationError):
        SensorTelemetryPayload(**make_valid_payload(battery_level=-1))

    # 5. wifi_rssi valid range (-120 to 0)
    p3 = SensorTelemetryPayload(**make_valid_payload(wifi_rssi=-70))
    assert p3.wifi_rssi == -70
    with pytest.raises(ValidationError):
        SensorTelemetryPayload(**make_valid_payload(wifi_rssi=10))


def test_extra_fields_forbidden() -> None:
    # Extra fields must be rejected (extra="forbid")
    data = make_valid_payload(unknown_sensor_field="malicious_or_unknown_data")
    with pytest.raises(ValidationError) as exc:
        SensorTelemetryPayload(**data)
    assert "extra_forbidden" in str(exc.value) or "Extra inputs are not permitted" in str(exc.value)


def test_naive_datetime_rejected() -> None:
    # Naive datetimes (without timezone offset) must be rejected
    naive_dt = datetime(2026, 9, 27, 10, 30, 0)
    data = make_valid_payload(timestamp=naive_dt)
    with pytest.raises(ValidationError) as exc:
        SensorTelemetryPayload(**data)
    assert "Timestamp must be timezone-aware" in str(exc.value)


def test_timezone_normalized_to_utc() -> None:
    # Non-UTC timezone is converted to UTC
    tz_plus_2 = timezone(timedelta(hours=2))
    dt_with_tz = datetime(2026, 9, 27, 12, 30, 0, tzinfo=tz_plus_2)
    data = make_valid_payload(timestamp=dt_with_tz)
    p = SensorTelemetryPayload(**data)
    assert p.timestamp.tzinfo == UTC
