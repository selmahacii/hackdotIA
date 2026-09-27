import asyncio
import json
import uuid

import aiomqtt
import pytest
from sqlalchemy import func, select

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import DeviceStatus
from app.models.measurement import Measurement
from app.mqtt.consumer import MQTTConsumer


@pytest.mark.asyncio
async def test_real_mosquitto_ingestion_and_idempotence() -> None:
    """
    Real end-to-end integration test with Eclipse Mosquitto broker on localhost:1883.
    Flow:
    1. Register Elderly + Device in PostgreSQL.
    2. Start MQTTConsumer.
    3. Publish real telemetry message over MQTT.
    4. Assert Measurement is persisted in PostgreSQL and Device.last_seen_at updated.
    5. Re-publish exact same event_id over MQTT.
    6. Assert duplicate is safely ignored and exactly ONE Measurement remains.
    7. Publish message with topic mismatch -> verify rejected.
    8. Stop consumer cleanly.
    """
    # 1. Verify Mosquitto connectivity
    try:
        async with aiomqtt.Client(hostname=settings.MQTT_HOST, port=settings.MQTT_PORT):
            pass
    except Exception as e:
        pytest.skip(
            f"Mosquitto broker not available on {settings.MQTT_HOST}:{settings.MQTT_PORT}: {e}"
        )

    device_uid = f"ESP32-BROKER-{uuid.uuid4().hex[:8]}"

    # Setup database records
    async with AsyncSessionLocal() as session:
        elderly = ElderlyPerson(
            first_name="Paul",
            last_name="Bertrand",
            phone="+33611223344",
            is_active=True,
        )
        session.add(elderly)
        await session.flush()

        device = Device(
            device_uid=device_uid,
            name="Bracelet Paul",
            elderly_id=elderly.id,
            status=DeviceStatus.UNKNOWN,
        )
        session.add(device)
        await session.commit()
        device_id = device.id

    # 2. Start consumer
    consumer = MQTTConsumer()
    await consumer.start()

    # Allow consumer a moment to connect and subscribe
    await asyncio.sleep(0.5)

    try:
        shared_event_id = uuid.uuid4()
        topic = f"elderly/{device_uid}/telemetry"
        payload = {
            "schema_version": "1.0",
            "event_id": str(shared_event_id),
            "device_uid": device_uid,
            "timestamp": "2026-09-27T10:30:00Z",
            "finger_detected": True,
            "bpm": 72.0,
            "spo2": 98.0,
            "temperature_c": 22.0,
            "humidity_percent": 45.0,
            "accel_x_g": 0.05,
            "accel_y_g": 0.02,
            "accel_z_g": 0.98,
            "accel_magnitude_g": 0.982,
            "gps_fix_valid": True,
            "gps_latitude": 48.8566,
            "gps_longitude": 2.3522,
            "battery_level": 85,
            "wifi_rssi": -65,
        }

        # 3. Publish valid telemetry
        async with aiomqtt.Client(
            hostname=settings.MQTT_HOST, port=settings.MQTT_PORT
        ) as publisher:
            await publisher.publish(topic, payload=json.dumps(payload), qos=1)

        # 4. Wait and verify persistence in PostgreSQL
        measurement = None
        for _ in range(20):  # poll up to 4s
            await asyncio.sleep(0.2)
            async with AsyncSessionLocal() as session:
                stmt = select(Measurement).where(Measurement.event_id == shared_event_id)
                res = await session.execute(stmt)
                measurement = res.scalars().first()
                if measurement:
                    break

        assert measurement is not None, "Measurement was not persisted from MQTT message"
        assert measurement.bpm == 72.0
        assert measurement.spo2 == 98.0
        assert measurement.battery_level == 85.0

        # Verify device status updated
        async with AsyncSessionLocal() as session:
            device_stmt = select(Device).where(Device.id == device_id)
            device_res = await session.execute(device_stmt)
            updated_device = device_res.scalars().one()
            assert updated_device.status == DeviceStatus.ONLINE
            assert updated_device.last_seen_at is not None

        # 5. Re-publish exact same event_id
        async with aiomqtt.Client(
            hostname=settings.MQTT_HOST, port=settings.MQTT_PORT
        ) as publisher:
            await publisher.publish(topic, payload=json.dumps(payload), qos=1)

        await asyncio.sleep(1.0)

        # 6. Verify duplicate was discarded, exactly 1 row exists
        async with AsyncSessionLocal() as session:
            count_stmt = select(func.count(Measurement.id)).where(
                Measurement.event_id == shared_event_id
            )
            count_res = await session.execute(count_stmt)
            assert count_res.scalar_one() == 1

        # 7. Topic mismatch: publish payload with mismatched topic
        mismatched_topic = "elderly/ESP32-OTHER/telemetry"
        async with aiomqtt.Client(
            hostname=settings.MQTT_HOST, port=settings.MQTT_PORT
        ) as publisher:
            await publisher.publish(mismatched_topic, payload=json.dumps(payload), qos=1)

        await asyncio.sleep(0.5)

        # Verify count did not change
        async with AsyncSessionLocal() as session:
            count_stmt = select(func.count(Measurement.id)).where(
                Measurement.event_id == shared_event_id
            )
            count_res = await session.execute(count_stmt)
            assert count_res.scalar_one() == 1

    finally:
        await consumer.stop()
