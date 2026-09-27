# ruff: noqa: E402
import asyncio
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import aiomqtt
from sqlalchemy import select

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import DeviceStatus
from app.models.measurement import Measurement
from app.models.sensor_health import SensorHealth
from app.mqtt.consumer import MQTTConsumer


async def run_demonstration() -> None:
    print("=" * 80)
    print("PHASE 4 LIVE DEMONSTRATION: DETERMINISTIC PROCESSING & SENSOR HEALTH PIPELINE")
    print("=" * 80)

    device_uid = "ESP32-PHASE4-DEMO"

    # Step 1: Provision demo ElderlyPerson and Device
    print(f"\n[STEP 1] Provisioning {device_uid} in PostgreSQL...")
    async with AsyncSessionLocal() as session:
        dev_stmt = select(Device).where(Device.device_uid == device_uid)
        res = await session.execute(dev_stmt)
        device = res.scalars().first()

        if not device:
            elderly = ElderlyPerson(
                first_name="Suzanne",
                last_name="Lenglen",
                phone="+33611998877",
                emergency_contact_name="Marc Lenglen",
                emergency_contact_phone="+33622889900",
                is_active=True,
            )
            session.add(elderly)
            await session.flush()

            device = Device(
                device_uid=device_uid,
                name="Bracelet Suzanne",
                elderly_id=elderly.id,
                status=DeviceStatus.UNKNOWN,
            )
            session.add(device)
            await session.commit()
            print(f"  -> Created ElderlyPerson: {elderly.first_name} {elderly.last_name}")
            print(f"  -> Created Device: {device.name} (uid={device.device_uid})")
        else:
            print(f"  -> Found existing device: {device.name} (uid={device.device_uid})")

    # Step 2: Start embedded MQTT Consumer
    print("\n[STEP 2] Starting MQTTConsumer connected to Mosquitto (localhost:1883)...")
    consumer = MQTTConsumer()
    await consumer.start()
    await asyncio.sleep(0.5)
    print("  -> MQTTConsumer active and subscribed to 'elderly/+/telemetry'.")

    try:
        # Step 3: Publish Healthy Telemetry Payload
        print("\n[STEP 3] Publishing Healthy Telemetry over Mosquitto MQTT...")
        healthy_event_id = uuid.uuid4()
        topic = f"elderly/{device_uid}/telemetry"
        healthy_payload = {
            "schema_version": "1.0",
            "event_id": str(healthy_event_id),
            "device_uid": device_uid,
            "timestamp": datetime.now(UTC).isoformat(),
            "finger_detected": True,
            "bpm": 74.0,
            "spo2": 98.5,
            "temperature_c": 22.0,
            "humidity_percent": 45.0,
            "accel_x_g": 0.01,
            "accel_y_g": 0.02,
            "accel_z_g": 0.99,
            "accel_magnitude_g": 0.991,
            "gps_fix_valid": True,
            "gps_latitude": 48.8584,
            "gps_longitude": 2.2945,
            "battery_level": 89,
            "wifi_rssi": -55,
        }

        async with aiomqtt.Client(
            hostname=settings.MQTT_HOST, port=settings.MQTT_PORT
        ) as publisher:
            await publisher.publish(topic, payload=json.dumps(healthy_payload), qos=1)
        print(f"  -> Published message (event_id={healthy_event_id}) to topic '{topic}'.")

        # Step 4: Verify PostgreSQL persistence for Measurement & SensorHealth
        print("\n[STEP 4] Verifying Measurement and SensorHealth in PostgreSQL...")
        healthy_health: SensorHealth | None = None
        for _ in range(25):
            await asyncio.sleep(0.2)
            async with AsyncSessionLocal() as session:
                meas_stmt = select(Measurement).where(Measurement.event_id == healthy_event_id)
                meas_res = await session.execute(meas_stmt)
                meas = meas_res.scalars().first()
                if meas:
                    h_stmt = select(SensorHealth).where(SensorHealth.measurement_id == meas.id)
                    h_res = await session.execute(h_stmt)
                    healthy_health = h_res.scalars().first()
                    if healthy_health:
                        print(f"  -> Measurement ID: {meas.id}")
                        print(
                            f"     BPM: {meas.bpm}, SpO2: {meas.spo2}%, Battery: {meas.battery_level}%"
                        )
                        print(f"  -> SensorHealth ID: {healthy_health.id}")
                        print(f"     MAX30102 Status: {healthy_health.max30102_status.value}")
                        print(f"     DHT11 Status:    {healthy_health.dht11_status.value}")
                        print(f"     MPU6050 Status:  {healthy_health.mpu6050_status.value}")
                        print(f"     GPS Status:      {healthy_health.gps_status.value}")
                        print(
                            f"     Battery Status:  {healthy_health.details.get('battery', {}).get('status') if healthy_health.details else 'N/A'}"
                        )
                        break

        if not healthy_health:
            print("  [ERROR] Healthy SensorHealth not found in time!")
            return

        # Step 5: Publish Degraded Telemetry Payload (No contact + GPS invalid)
        print("\n[STEP 5] Publishing Degraded Telemetry (No finger detected + No GPS fix)...")
        degraded_event_id = uuid.uuid4()
        degraded_payload = {
            "schema_version": "1.0",
            "event_id": str(degraded_event_id),
            "device_uid": device_uid,
            "timestamp": datetime.now(UTC).isoformat(),
            "finger_detected": False,
            "bpm": None,
            "spo2": None,
            "temperature_c": 22.1,
            "humidity_percent": 45.2,
            "accel_x_g": 0.0,
            "accel_y_g": 0.0,
            "accel_z_g": 1.0,
            "accel_magnitude_g": 1.0,
            "gps_fix_valid": False,
            "battery_level": 18,
            "wifi_rssi": -68,
        }

        async with aiomqtt.Client(
            hostname=settings.MQTT_HOST, port=settings.MQTT_PORT
        ) as publisher:
            await publisher.publish(topic, payload=json.dumps(degraded_payload), qos=1)
        print(f"  -> Published degraded message (event_id={degraded_event_id}) to topic '{topic}'.")

        # Step 6: Verify Degraded SensorHealth
        print("\n[STEP 6] Verifying Degraded SensorHealth in PostgreSQL...")
        degraded_health: SensorHealth | None = None
        for _ in range(25):
            await asyncio.sleep(0.2)
            async with AsyncSessionLocal() as session:
                meas_stmt = select(Measurement).where(Measurement.event_id == degraded_event_id)
                meas_res = await session.execute(meas_stmt)
                meas = meas_res.scalars().first()
                if meas:
                    h_stmt = select(SensorHealth).where(SensorHealth.measurement_id == meas.id)
                    h_res = await session.execute(h_stmt)
                    degraded_health = h_res.scalars().first()
                    if degraded_health:
                        print(f"  -> Measurement ID: {meas.id}")
                        print(f"     Finger detected: {meas.finger_detected}")
                        print(f"  -> SensorHealth ID: {degraded_health.id}")
                        print(
                            f"     MAX30102 Status: {degraded_health.max30102_status.value} (Reason: {degraded_health.details.get('reasons', {}).get('max30102') if degraded_health.details else 'N/A'})"
                        )
                        print(
                            f"     Battery Status:  {degraded_health.details.get('battery', {}).get('status') if degraded_health.details else 'N/A'} (Level: {degraded_health.details.get('battery', {}).get('level') if degraded_health.details else 'N/A'}%)"
                        )
                        break

        if not degraded_health:
            print("  [ERROR] Degraded SensorHealth not found in time!")
            return

        print("\n" + "=" * 80)
        print("DEMO SUCCESS: End-to-end deterministic processing pipeline verified!")
        print("=" * 80)

    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_demonstration())
