import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.device import Device
from app.models.enums import DeviceStatus, SensorHealthStatus
from app.models.measurement import Measurement
from app.services.sensor_health import SensorHealthService


def create_dummy_measurement(
    measured_at: datetime,
    finger_detected: bool = True,
    bpm: float | None = 75.0,
    spo2: float | None = 98.0,
    temperature_c: float | None = 22.0,
    humidity_percent: float | None = 50.0,
    accel_x_g: float | None = 0.02,
    accel_y_g: float | None = 0.01,
    accel_z_g: float | None = 0.99,
    accel_magnitude_g: float | None = 0.99,
    gps_fix_valid: bool = True,
    gps_latitude: float | None = 48.8566,
    gps_longitude: float | None = 2.3522,
    battery_level: float | None = 85.0,
    wifi_rssi: int | None = -65,
) -> Measurement:
    return Measurement(
        id=uuid.uuid4(),
        device_id=uuid.uuid4(),
        elderly_id=uuid.uuid4(),
        received_at=measured_at,
        measured_at=measured_at,
        finger_detected=finger_detected,
        bpm=bpm,
        spo2=spo2,
        temperature_c=temperature_c,
        humidity_percent=humidity_percent,
        accel_x_g=accel_x_g,
        accel_y_g=accel_y_g,
        accel_z_g=accel_z_g,
        accel_magnitude_g=accel_magnitude_g,
        gps_fix_valid=gps_fix_valid,
        gps_latitude=gps_latitude,
        gps_longitude=gps_longitude,
        battery_level=battery_level,
        wifi_rssi=wifi_rssi,
    )


@pytest.fixture
def service() -> SensorHealthService:
    return SensorHealthService()


# 1. Healthy MAX30102
def test_max30102_healthy(service: SensorHealthService) -> None:
    now = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    m = create_dummy_measurement(now, finger_detected=True, bpm=78.0, spo2=98.0)
    eval_result = service.evaluate(m)
    assert eval_result.max30102_status == SensorHealthStatus.HEALTHY
    assert eval_result.details["reasons"]["max30102"] is None


# 2. Finger removed
def test_max30102_finger_removed(service: SensorHealthService) -> None:
    now = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    m = create_dummy_measurement(now, finger_detected=False, bpm=None, spo2=None)
    eval_result = service.evaluate(m)
    assert eval_result.max30102_status == SensorHealthStatus.NO_CONTACT
    assert eval_result.details["reasons"]["max30102"] == "finger_not_detected"


# 3. BPM absent with movement >= 60s
def test_max30102_bpm_absent_with_movement(service: SensorHealthService) -> None:
    t0 = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    t1 = t0 + timedelta(seconds=70)

    # Past measurement 70 seconds ago with finger detected, no bpm, and movement
    h1 = create_dummy_measurement(
        t0, finger_detected=True, bpm=None, spo2=None, accel_magnitude_g=1.4
    )
    # Current measurement
    m = create_dummy_measurement(
        t1, finger_detected=True, bpm=None, spo2=None, accel_magnitude_g=1.3
    )

    eval_result = service.evaluate(m, history=[h1])
    assert eval_result.max30102_status == SensorHealthStatus.SUSPECT
    assert eval_result.details["reasons"]["max30102"] == "bpm_absent_with_movement"


# 4. BPM absent without movement >= 60s
def test_max30102_bpm_absent_no_movement(service: SensorHealthService) -> None:
    t0 = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    t1 = t0 + timedelta(seconds=70)

    h1 = create_dummy_measurement(
        t0, finger_detected=True, bpm=None, spo2=None, accel_magnitude_g=1.0
    )
    m = create_dummy_measurement(
        t1, finger_detected=True, bpm=None, spo2=None, accel_magnitude_g=1.0
    )

    eval_result = service.evaluate(m, history=[h1])
    assert eval_result.max30102_status == SensorHealthStatus.UNKNOWN
    assert eval_result.details["reasons"]["max30102"] == "bpm_absent_no_movement"


# 5. DHT11 normal
def test_dht11_healthy(service: SensorHealthService) -> None:
    t0 = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    t1 = t0 + timedelta(seconds=10)

    h1 = create_dummy_measurement(t0, temperature_c=21.0, humidity_percent=45.0)
    m = create_dummy_measurement(t1, temperature_c=21.5, humidity_percent=46.0)

    eval_result = service.evaluate(m, history=[h1])
    assert eval_result.dht11_status == SensorHealthStatus.HEALTHY
    assert eval_result.details["reasons"]["dht11"] is None


# 6. DHT11 sampling too fast (< 2.0s)
def test_dht11_sampling_too_fast(service: SensorHealthService) -> None:
    t0 = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    t1 = t0 + timedelta(seconds=1.2)  # 1.2s < 2.0s

    h1 = create_dummy_measurement(t0, temperature_c=21.0, humidity_percent=45.0)
    m = create_dummy_measurement(t1, temperature_c=21.1, humidity_percent=45.2)

    eval_result = service.evaluate(m, history=[h1])
    assert eval_result.dht11_status == SensorHealthStatus.SUSPECT
    assert eval_result.details["reasons"]["dht11"] == "dht11_sampling_too_fast"


# 7. DHT11 humidity frozen (same humidity for >= 300s with >= 3 samples)
def test_dht11_humidity_frozen(service: SensorHealthService) -> None:
    t0 = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    t1 = t0 + timedelta(seconds=150)
    t2 = t0 + timedelta(seconds=320)  # > 300s total

    h1 = create_dummy_measurement(t0, humidity_percent=55.0)
    h2 = create_dummy_measurement(t1, humidity_percent=55.0)
    m = create_dummy_measurement(t2, humidity_percent=55.0)

    eval_result = service.evaluate(m, history=[h1, h2])
    assert eval_result.dht11_status == SensorHealthStatus.SUSPECT
    assert eval_result.details["reasons"]["dht11"] == "humidity_frozen"


# 8. MPU6050 normal
def test_mpu6050_healthy(service: SensorHealthService) -> None:
    now = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    m = create_dummy_measurement(now, accel_x_g=0.03, accel_y_g=0.01, accel_z_g=0.98)
    eval_result = service.evaluate(m)
    assert eval_result.mpu6050_status == SensorHealthStatus.HEALTHY
    assert eval_result.details["reasons"]["mpu6050"] is None


# 9. MPU6050 flatline (>= 5 consecutive zero samples)
def test_mpu6050_flatline(service: SensorHealthService) -> None:
    t0 = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    history = [
        create_dummy_measurement(
            t0 + timedelta(seconds=i * 5),
            accel_x_g=0.0,
            accel_y_g=0.0,
            accel_z_g=0.0,
        )
        for i in range(4)
    ]
    # Current is the 5th zero sample
    m = create_dummy_measurement(
        t0 + timedelta(seconds=20),
        accel_x_g=0.0,
        accel_y_g=0.0,
        accel_z_g=0.0,
    )

    eval_result = service.evaluate(m, history=history)
    assert eval_result.mpu6050_status == SensorHealthStatus.SUSPECT
    assert eval_result.details["reasons"]["mpu6050"] == "imu_flatline"


# 10. GPS valid fix
def test_gps_healthy(service: SensorHealthService) -> None:
    now = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    m = create_dummy_measurement(
        now, gps_fix_valid=True, gps_latitude=48.8566, gps_longitude=2.3522
    )
    eval_result = service.evaluate(m)
    assert eval_result.gps_status == SensorHealthStatus.HEALTHY
    assert eval_result.details["reasons"]["gps"] is None


# 11. GPS no fix < 180s
def test_gps_no_fix_searching(service: SensorHealthService) -> None:
    t0 = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    t1 = t0 + timedelta(seconds=60)  # 60s < 180s

    h1 = create_dummy_measurement(t0, gps_fix_valid=False, gps_latitude=None, gps_longitude=None)
    m = create_dummy_measurement(t1, gps_fix_valid=False, gps_latitude=None, gps_longitude=None)

    eval_result = service.evaluate(m, history=[h1])
    assert eval_result.gps_status == SensorHealthStatus.NO_CONTACT
    assert eval_result.details["reasons"]["gps"] == "gps_searching_fix"


# 12. GPS no fix > 180s
def test_gps_no_fix_unavailable(service: SensorHealthService) -> None:
    t0 = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    t1 = t0 + timedelta(seconds=200)  # 200s > 180s

    h1 = create_dummy_measurement(t0, gps_fix_valid=False, gps_latitude=None, gps_longitude=None)
    m = create_dummy_measurement(t1, gps_fix_valid=False, gps_latitude=None, gps_longitude=None)

    eval_result = service.evaluate(m, history=[h1])
    assert eval_result.gps_status == SensorHealthStatus.UNAVAILABLE
    assert eval_result.details["reasons"]["gps"] == "gps_no_fix"


# 13. Device online
def test_device_online(service: SensorHealthService) -> None:
    now = datetime(2026, 9, 27, 10, 0, 30, tzinfo=UTC)
    last_seen = datetime(2026, 9, 27, 10, 0, 0, tzinfo=UTC)  # 30s ago <= 60s
    device = Device(
        id=uuid.uuid4(),
        device_uid="ESP32-TEST",
        elderly_id=uuid.uuid4(),
        status=DeviceStatus.ONLINE,
        last_seen_at=last_seen,
    )
    m = create_dummy_measurement(now)
    eval_result = service.evaluate(m, device=device, now=now)
    assert eval_result.details["device"]["status"] == "ONLINE"
    assert eval_result.details["device"]["reason"] is None


# 14. Device offline > 60s
def test_device_offline(service: SensorHealthService) -> None:
    now = datetime(2026, 9, 27, 10, 2, 0, tzinfo=UTC)
    last_seen = datetime(2026, 9, 27, 10, 0, 0, tzinfo=UTC)  # 120s ago > 60s
    device = Device(
        id=uuid.uuid4(),
        device_uid="ESP32-TEST",
        elderly_id=uuid.uuid4(),
        status=DeviceStatus.ONLINE,
        last_seen_at=last_seen,
    )
    m = create_dummy_measurement(now)
    eval_result = service.evaluate(m, device=device, now=now)
    assert eval_result.details["device"]["status"] == "UNAVAILABLE"
    assert eval_result.details["device"]["reason"] == "device_offline"


# 15. Battery normal (>= 20%)
def test_battery_normal(service: SensorHealthService) -> None:
    now = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    m = create_dummy_measurement(now, battery_level=55.0)
    eval_result = service.evaluate(m)
    assert eval_result.details["battery"]["status"] == "NORMAL"


# 16. Battery warning (< 20% and >= 10%)
def test_battery_warning(service: SensorHealthService) -> None:
    now = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    m = create_dummy_measurement(now, battery_level=15.0)
    eval_result = service.evaluate(m)
    assert eval_result.details["battery"]["status"] == "WARNING"


# 17. Battery critical (< 10%)
def test_battery_critical(service: SensorHealthService) -> None:
    now = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    m = create_dummy_measurement(now, battery_level=8.0)
    eval_result = service.evaluate(m)
    assert eval_result.details["battery"]["status"] == "CRITICAL"
