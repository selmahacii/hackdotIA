import asyncio
import json
import uuid
from datetime import UTC, datetime

import aiomqtt
import pytest
from sqlalchemy import func, select

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.alert import Alert
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import DeviceStatus, SensorHealthStatus
from app.models.measurement import Measurement
from app.models.sensor_health import SensorHealth
from app.mqtt.consumer import MQTTConsumer


@pytest.mark.asyncio
async def test_firmware_contract_all_cases_e2e() -> None:
    """
    Exhaustive integration test covering all 5 firmware operational cases:
    - Cas A: Nominal (all sensors valid, persisted to Measurement and SensorHealth)
    - Cas B: Finger absent (finger=false, bpm=null, spo2=null -> SensorHealth NO_CONTACT)
    - Cas C: GPS no fix (gps_fix=false, coords=null -> accepted; coords=0.0 -> rejected)
    - Cas D: High movement / spike > 2.8g (persisted, zero local alert created in DB)
    - Cas E: Retry idempotence (same event_id -> exactly 1 Measurement)
    """
    try:
        async with aiomqtt.Client(hostname=settings.MQTT_HOST, port=settings.MQTT_PORT):
            pass
    except Exception as e:
        pytest.skip(f"Mosquitto broker not available: {e}")

    device_uid = "ESP32-ELDERLY-001"

    # Setup DB entities
    async with AsyncSessionLocal() as session:
        # Check if already present
        dev_stmt = select(Device).where(Device.device_uid == device_uid)
        dev_res = await session.execute(dev_stmt)
        device = dev_res.scalars().first()

        if not device:
            elderly = ElderlyPerson(
                first_name="Albert",
                last_name="Camus",
                phone="+33699887766",
                is_active=True,
            )
            session.add(elderly)
            await session.flush()

            device = Device(
                device_uid=device_uid,
                name="Bracelet Albert",
                elderly_id=elderly.id,
                status=DeviceStatus.UNKNOWN,
            )
            session.add(device)
            await session.commit()

    consumer = MQTTConsumer()
    await consumer.start()
    await asyncio.sleep(0.5)

    topic = f"elderly/{device_uid}/telemetry"

    try:
        # -------------------------------------------------------------
        # CAS A: Nominal
        # -------------------------------------------------------------
        event_id_a = uuid.uuid4()
        payload_a = {
            "schema_version": "1.0",
            "event_id": str(event_id_a),
            "device_uid": device_uid,
            "timestamp": datetime.now(UTC).isoformat(),
            "finger_detected": True,
            "bpm": 74.0,
            "spo2": 98.0,
            "temperature_c": 22.0,
            "humidity_percent": 45.0,
            "accel_x_g": 0.01,
            "accel_y_g": 0.02,
            "accel_z_g": 0.99,
            "accel_magnitude_g": 0.99,
            "gps_fix_valid": True,
            "gps_latitude": 36.75,
            "gps_longitude": 3.06,
            "battery_level": 89,
            "wifi_rssi": -55,
        }

        async with aiomqtt.Client(hostname=settings.MQTT_HOST, port=settings.MQTT_PORT) as pub:
            await pub.publish(topic, payload=json.dumps(payload_a), qos=1)

        meas_a = None
        for _ in range(25):
            await asyncio.sleep(0.2)
            async with AsyncSessionLocal() as session:
                meas_stmt = select(Measurement).where(Measurement.event_id == event_id_a)
                res = await session.execute(meas_stmt)
                meas_a = res.scalars().first()
                if meas_a:
                    break

        assert meas_a is not None, "Cas A: Measurement not persisted"
        assert meas_a.bpm == 74.0
        assert meas_a.temperature_c == 22.0
        assert meas_a.gps_latitude == 36.75

        # -------------------------------------------------------------
        # CAS B: Doigt absent (finger=false, bpm=null, spo2=null)
        # -------------------------------------------------------------
        event_id_b = uuid.uuid4()
        payload_b = {
            "schema_version": "1.0",
            "event_id": str(event_id_b),
            "device_uid": device_uid,
            "timestamp": datetime.now(UTC).isoformat(),
            "finger_detected": False,
            "bpm": None,
            "spo2": None,
            "temperature_c": 22.0,
            "humidity_percent": 45.0,
            "accel_x_g": 0.01,
            "accel_y_g": 0.02,
            "accel_z_g": 0.99,
            "accel_magnitude_g": 0.99,
            "gps_fix_valid": True,
            "gps_latitude": 36.75,
            "gps_longitude": 3.06,
        }

        async with aiomqtt.Client(hostname=settings.MQTT_HOST, port=settings.MQTT_PORT) as pub:
            await pub.publish(topic, payload=json.dumps(payload_b), qos=1)

        meas_b = None
        health_b = None
        for _ in range(25):
            await asyncio.sleep(0.2)
            async with AsyncSessionLocal() as session:
                meas_stmt = select(Measurement).where(Measurement.event_id == event_id_b)
                res = await session.execute(meas_stmt)
                meas_b = res.scalars().first()
                if meas_b:
                    h_stmt = select(SensorHealth).where(SensorHealth.measurement_id == meas_b.id)
                    h_res = await session.execute(h_stmt)
                    health_b = h_res.scalars().first()
                    if health_b:
                        break

        assert meas_b is not None, "Cas B: Measurement not persisted"
        assert meas_b.finger_detected is False
        assert meas_b.bpm is None
        assert meas_b.spo2 is None
        assert health_b is not None, "Cas B: SensorHealth not evaluated"
        assert health_b.max30102_status == SensorHealthStatus.NO_CONTACT

        # -------------------------------------------------------------
        # CAS C: GPS sans fix (gps_fix=false, coords=null)
        # -------------------------------------------------------------
        event_id_c = uuid.uuid4()
        payload_c = {
            "schema_version": "1.0",
            "event_id": str(event_id_c),
            "device_uid": device_uid,
            "timestamp": datetime.now(UTC).isoformat(),
            "gps_fix_valid": False,
            "gps_latitude": None,
            "gps_longitude": None,
        }

        async with aiomqtt.Client(hostname=settings.MQTT_HOST, port=settings.MQTT_PORT) as pub:
            await pub.publish(topic, payload=json.dumps(payload_c), qos=1)

        meas_c = None
        for _ in range(25):
            await asyncio.sleep(0.2)
            async with AsyncSessionLocal() as session:
                meas_stmt = select(Measurement).where(Measurement.event_id == event_id_c)
                res = await session.execute(meas_stmt)
                meas_c = res.scalars().first()
                if meas_c:
                    break

        assert meas_c is not None, "Cas C: Measurement not persisted"
        assert meas_c.gps_fix_valid is False
        assert meas_c.gps_latitude is None
        assert meas_c.gps_longitude is None

        # Verify that sending 0.0 with gps_fix_valid=false is rejected!
        bad_gps_event_id = uuid.uuid4()
        bad_gps_payload = {
            "schema_version": "1.0",
            "event_id": str(bad_gps_event_id),
            "device_uid": device_uid,
            "timestamp": datetime.now(UTC).isoformat(),
            "gps_fix_valid": False,
            "gps_latitude": 0.0,
            "gps_longitude": 0.0,
        }
        async with aiomqtt.Client(hostname=settings.MQTT_HOST, port=settings.MQTT_PORT) as pub:
            await pub.publish(topic, payload=json.dumps(bad_gps_payload), qos=1)

        await asyncio.sleep(0.5)
        async with AsyncSessionLocal() as session:
            count_stmt = select(func.count(Measurement.id)).where(
                Measurement.event_id == bad_gps_event_id
            )
            count_res = await session.execute(count_stmt)
            assert (
                count_res.scalar_one() == 0
            ), "Null Island 0.0 coordinate was erroneously ingested"

        # -------------------------------------------------------------
        # CAS D: Mouvement important (pic d'accélération > 2.8g)
        # -------------------------------------------------------------
        event_id_d = uuid.uuid4()
        payload_d = {
            "schema_version": "1.0",
            "event_id": str(event_id_d),
            "device_uid": device_uid,
            "timestamp": datetime.now(UTC).isoformat(),
            "accel_x_g": 1.8,
            "accel_y_g": 1.5,
            "accel_z_g": 2.2,
            "accel_magnitude_g": 3.21,
        }

        async with aiomqtt.Client(hostname=settings.MQTT_HOST, port=settings.MQTT_PORT) as pub:
            await pub.publish(topic, payload=json.dumps(payload_d), qos=1)

        meas_d = None
        for _ in range(25):
            await asyncio.sleep(0.2)
            async with AsyncSessionLocal() as session:
                meas_stmt = select(Measurement).where(Measurement.event_id == event_id_d)
                res = await session.execute(meas_stmt)
                meas_d = res.scalars().first()
                if meas_d:
                    break

        assert meas_d is not None, "Cas D: Measurement not persisted"
        assert meas_d.accel_magnitude_g == 3.21

        # CRITICAL: Verify NO official Alert was created in database!
        async with AsyncSessionLocal() as session:
            alert_stmt = select(func.count(Alert.id)).where(Alert.device_id == device.id)
            alert_res = await session.execute(alert_stmt)
            # The firmware spike did NOT create an official Alert!
            assert (
                alert_res.scalar_one() == 0
            ), "Spike > 2.8g erroneously triggered an official Alert"

        # -------------------------------------------------------------
        # CAS E: Retry idempotent (même payload retransmis)
        # -------------------------------------------------------------
        async with aiomqtt.Client(hostname=settings.MQTT_HOST, port=settings.MQTT_PORT) as pub:
            await pub.publish(topic, payload=json.dumps(payload_a), qos=1)

        await asyncio.sleep(0.8)

        async with AsyncSessionLocal() as session:
            count_stmt = select(func.count(Measurement.id)).where(
                Measurement.event_id == event_id_a
            )
            count_res = await session.execute(count_stmt)
            assert count_res.scalar_one() == 1, "Duplicate MQTT message created extra Measurement"

    finally:
        await consumer.stop()
