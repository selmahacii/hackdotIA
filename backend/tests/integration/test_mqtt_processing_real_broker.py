import asyncio
import json
import uuid
from datetime import UTC, datetime

import aiomqtt
import pytest
from sqlalchemy import select

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import DeviceStatus, SensorHealthStatus
from app.models.measurement import Measurement
from app.models.sensor_health import SensorHealth
from app.mqtt.consumer import MQTTConsumer


@pytest.mark.asyncio
async def test_real_mqtt_processing_pipeline_end_to_end() -> None:
    """
    End-to-end integration test with real Mosquitto broker and real PostgreSQL:
    ESP32 MQTT publish -> MQTTConsumer -> Pydantic -> PostgreSQL Measurement
    -> ProcessingService -> PostgreSQL SensorHealth.
    """
    # 1. Verify Mosquitto connectivity
    try:
        async with aiomqtt.Client(hostname=settings.MQTT_HOST, port=settings.MQTT_PORT):
            pass
    except Exception as e:
        pytest.skip(
            f"Mosquitto broker not available on {settings.MQTT_HOST}:{settings.MQTT_PORT}: {e}"
        )

    device_uid = f"ESP32-E2E-{uuid.uuid4().hex[:8]}"

    # 2. Setup database entities
    async with AsyncSessionLocal() as session:
        elderly = ElderlyPerson(
            first_name="Charles",
            last_name="Aznavour",
            phone="+33655443322",
            is_active=True,
        )
        session.add(elderly)
        await session.flush()

        device = Device(
            device_uid=device_uid,
            name="Bracelet Charles",
            elderly_id=elderly.id,
            status=DeviceStatus.UNKNOWN,
        )
        session.add(device)
        await session.commit()
        device_id = device.id

    # 3. Start MQTTConsumer
    consumer = MQTTConsumer()
    await consumer.start()
    await asyncio.sleep(0.5)

    try:
        # 4. Publish healthy telemetry
        event_id_healthy = uuid.uuid4()
        topic = f"elderly/{device_uid}/telemetry"
        healthy_payload = {
            "schema_version": "1.0",
            "event_id": str(event_id_healthy),
            "device_uid": device_uid,
            "timestamp": datetime.now(UTC).isoformat(),
            "finger_detected": True,
            "bpm": 76.0,
            "spo2": 98.0,
            "temperature_c": 22.5,
            "humidity_percent": 48.0,
            "accel_x_g": 0.01,
            "accel_y_g": 0.02,
            "accel_z_g": 0.99,
            "accel_magnitude_g": 0.991,
            "gps_fix_valid": True,
            "gps_latitude": 48.8566,
            "gps_longitude": 2.3522,
            "battery_level": 82,
            "wifi_rssi": -62,
        }

        async with aiomqtt.Client(
            hostname=settings.MQTT_HOST, port=settings.MQTT_PORT
        ) as publisher:
            await publisher.publish(topic, payload=json.dumps(healthy_payload), qos=1)

        # 5. Poll for Measurement and SensorHealth in PostgreSQL
        meas_healthy: Measurement | None = None
        health_healthy: SensorHealth | None = None

        for _ in range(25):  # poll up to 5s
            await asyncio.sleep(0.2)
            async with AsyncSessionLocal() as session:
                meas_stmt = select(Measurement).where(Measurement.event_id == event_id_healthy)
                meas_res = await session.execute(meas_stmt)
                meas_healthy = meas_res.scalars().first()

                if meas_healthy:
                    health_stmt = select(SensorHealth).where(
                        SensorHealth.measurement_id == meas_healthy.id
                    )
                    health_res = await session.execute(health_stmt)
                    health_healthy = health_res.scalars().first()
                    if health_healthy:
                        break

        assert meas_healthy is not None, "Healthy measurement not persisted"
        assert health_healthy is not None, "SensorHealth not persisted for healthy measurement"
        assert health_healthy.device_id == device_id
        assert health_healthy.max30102_status == SensorHealthStatus.HEALTHY
        assert health_healthy.dht11_status == SensorHealthStatus.HEALTHY
        assert health_healthy.mpu6050_status == SensorHealthStatus.HEALTHY
        assert health_healthy.gps_status == SensorHealthStatus.HEALTHY
        assert health_healthy.details is not None
        assert health_healthy.details["battery"]["status"] == "NORMAL"

        # 6. Publish degraded telemetry (finger not detected)
        event_id_degraded = uuid.uuid4()
        degraded_payload = {
            "schema_version": "1.0",
            "event_id": str(event_id_degraded),
            "device_uid": device_uid,
            "timestamp": datetime.now(UTC).isoformat(),
            "finger_detected": False,
            "bpm": None,
            "spo2": None,
            "temperature_c": 22.5,
            "humidity_percent": 48.0,
            "accel_x_g": 0.01,
            "accel_y_g": 0.02,
            "accel_z_g": 0.99,
            "accel_magnitude_g": 0.991,
            "gps_fix_valid": False,
            "battery_level": 81,
            "wifi_rssi": -63,
        }

        async with aiomqtt.Client(
            hostname=settings.MQTT_HOST, port=settings.MQTT_PORT
        ) as publisher:
            await publisher.publish(topic, payload=json.dumps(degraded_payload), qos=1)

        # 7. Poll for degraded Measurement and SensorHealth
        health_degraded: SensorHealth | None = None
        for _ in range(25):
            await asyncio.sleep(0.2)
            async with AsyncSessionLocal() as session:
                meas_stmt = select(Measurement).where(Measurement.event_id == event_id_degraded)
                meas_res = await session.execute(meas_stmt)
                meas_degraded = meas_res.scalars().first()

                if meas_degraded:
                    health_stmt = select(SensorHealth).where(
                        SensorHealth.measurement_id == meas_degraded.id
                    )
                    health_res = await session.execute(health_stmt)
                    health_degraded = health_res.scalars().first()
                    if health_degraded:
                        break

        assert health_degraded is not None, "SensorHealth not persisted for degraded measurement"
        assert health_degraded.max30102_status == SensorHealthStatus.NO_CONTACT
        assert health_degraded.details is not None
        assert health_degraded.details["reasons"]["max30102"] == "finger_not_detected"

    finally:
        await consumer.stop()
