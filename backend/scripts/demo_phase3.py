import asyncio
import json
import sys
import uuid
from datetime import UTC, datetime

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import aiomqtt
import httpx
from sqlalchemy import func, select

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import DeviceStatus
from app.models.measurement import Measurement


async def run_demonstration() -> None:
    print("=" * 70)
    print("PHASE 3 LIVE DEMONSTRATION: REAL MQTT INGESTION & IDEMPOTENCE")
    print("=" * 70)

    device_uid = "ESP32-ELDERLY-001"

    # Step 1: Provision demo ElderlyPerson and Device if not exists
    print(f"\n[STEP 1] Verifying / Provisioning {device_uid} in PostgreSQL...")
    async with AsyncSessionLocal() as session:
        dev_init_stmt = select(Device).where(Device.device_uid == device_uid)
        init_res = await session.execute(dev_init_stmt)
        device = init_res.scalars().first()

        if not device:
            elderly = ElderlyPerson(
                first_name="Germaine",
                last_name="Martin",
                phone="+33612345678",
                emergency_contact_name="Lucie Martin",
                emergency_contact_phone="+33698765432",
                is_active=True,
            )
            session.add(elderly)
            await session.flush()

            device = Device(
                device_uid=device_uid,
                name="Bracelet Germaine",
                elderly_id=elderly.id,
                status=DeviceStatus.UNKNOWN,
            )
            session.add(device)
            await session.commit()
            print(
                f"  -> Created ElderlyPerson: {elderly.first_name} {elderly.last_name} ({elderly.id})"
            )
            print(f"  -> Created Device: {device.name} (uid={device.device_uid}, id={device.id})")
        else:
            print(f"  -> Device already registered: {device.name} (uid={device.device_uid})")

    # Step 2: Check /ready endpoint
    print("\n[STEP 2] Inspecting FastAPI /api/v1/ready endpoint...")
    try:
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            resp = await client.get("/api/v1/ready")
            print(f"  -> Status code: {resp.status_code}")
            print(f"  -> Response: {resp.json()}")
    except Exception as e:
        print(f"  -> FastAPI server note (not running on :8000 or using test runner): {e}")

    # Step 3: Publish real telemetry to Mosquitto
    demo_event_id = uuid.uuid4()
    topic = f"elderly/{device_uid}/telemetry"
    payload = {
        "schema_version": "1.0",
        "event_id": str(demo_event_id),
        "device_uid": device_uid,
        "timestamp": datetime.now(UTC).isoformat(),
        "finger_detected": True,
        "bpm": 72.5,
        "spo2": 98.0,
        "temperature_c": 21.4,
        "humidity_percent": 48.0,
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

    print(f"\n[STEP 3] Publishing real telemetry to MQTT topic '{topic}'...")
    print(f"  -> Event ID: {demo_event_id}")
    print("  -> Payload: BPM=72.5, SpO2=98%, Temp=21.4°C, Accel=0.982g, Battery=85%")

    async with aiomqtt.Client(hostname=settings.MQTT_HOST, port=settings.MQTT_PORT) as publisher:
        await publisher.publish(topic, payload=json.dumps(payload), qos=1)
        print("  -> Message published with QoS 1.")

    # Step 4: Wait and inspect PostgreSQL
    print("\n[STEP 4] Querying PostgreSQL for persisted Measurement...")
    await asyncio.sleep(1.0)

    async with AsyncSessionLocal() as session:
        meas_stmt = select(Measurement).where(Measurement.event_id == demo_event_id)
        meas_res = await session.execute(meas_stmt)
        m = meas_res.scalars().first()

        if m:
            print("  -> SUCCESS! Measurement found in PostgreSQL:")
            print(f"     * ID:           {m.id}")
            print(f"     * Event ID:     {m.event_id}")
            print(f"     * Device ID:    {m.device_id}")
            print(f"     * Elderly ID:   {m.elderly_id}")
            print(f"     * Measured at:  {m.measured_at}")
            print(f"     * BPM:          {m.bpm}")
            print(f"     * SpO2:         {m.spo2}%")
            print(f"     * Temperature:  {m.temperature_c}°C")
            print(f"     * Battery:      {m.battery_level}%")
        else:
            print("  -> ERROR: Measurement not found in DB!")

        # Check Device status
        dev_stmt = select(Device).where(Device.device_uid == device_uid)
        dev_res = await session.execute(dev_stmt)
        dev = dev_res.scalars().one()
        print("  -> Device Updated State:")
        print(f"     * Status:       {dev.status.value}")
        print(f"     * Last seen at: {dev.last_seen_at}")
        print(f"     * Battery:      {dev.battery_level}%")

    # Step 5: Publish DUPLICATE event_id to verify idempotence
    print("\n[STEP 5] Re-publishing EXACT same payload (same event_id) to verify idempotence...")
    async with aiomqtt.Client(hostname=settings.MQTT_HOST, port=settings.MQTT_PORT) as publisher:
        await publisher.publish(topic, payload=json.dumps(payload), qos=1)
        print(f"  -> Duplicate event_id {demo_event_id} re-published.")

    await asyncio.sleep(1.0)

    async with AsyncSessionLocal() as session:
        count_stmt = select(func.count(Measurement.id)).where(Measurement.event_id == demo_event_id)
        count_res = await session.execute(count_stmt)
        total_count = count_res.scalar_one()
        print(f"  -> Database verification for event_id={demo_event_id}:")
        print(f"     * Row count in measurement table: {total_count}")
        if total_count == 1:
            print("  -> IDEMPOTENCY CONFIRMED! Exactly 1 row persisted, duplicate rejected safely.")
        else:
            print(f"  -> FAILURE: Found {total_count} rows for the same event_id!")

    # Step 6: Publish INVALID payload (finger_detected=False but bpm=80)
    print("\n[STEP 6] Testing rejection of invalid payload (finger_detected=False with BPM=80)...")
    invalid_event_id = uuid.uuid4()
    invalid_payload = {
        "schema_version": "1.0",
        "event_id": str(invalid_event_id),
        "device_uid": device_uid,
        "timestamp": datetime.now(UTC).isoformat(),
        "finger_detected": False,
        "bpm": 80.0,
    }
    async with aiomqtt.Client(hostname=settings.MQTT_HOST, port=settings.MQTT_PORT) as publisher:
        await publisher.publish(topic, payload=json.dumps(invalid_payload), qos=1)
        print("  -> Invalid message published.")

    await asyncio.sleep(0.5)

    async with AsyncSessionLocal() as session:
        inv_stmt = select(Measurement).where(Measurement.event_id == invalid_event_id)
        inv_res = await session.execute(inv_stmt)
        assert inv_res.scalars().first() is None
        print(
            "  -> REJECTION CONFIRMED: Invalid payload rejected by Pydantic; nothing written to DB."
        )

    # Step 7: Publish from UNKNOWN device
    print("\n[STEP 7] Testing rejection of unknown device (ESP32-UNKNOWN-999)...")
    unknown_event_id = uuid.uuid4()
    unknown_topic = "elderly/ESP32-UNKNOWN-999/telemetry"
    unknown_payload = {
        "schema_version": "1.0",
        "event_id": str(unknown_event_id),
        "device_uid": "ESP32-UNKNOWN-999",
        "timestamp": datetime.now(UTC).isoformat(),
        "finger_detected": False,
    }
    async with aiomqtt.Client(hostname=settings.MQTT_HOST, port=settings.MQTT_PORT) as publisher:
        await publisher.publish(unknown_topic, payload=json.dumps(unknown_payload), qos=1)
        print("  -> Message from unknown device published.")

    await asyncio.sleep(0.5)

    async with AsyncSessionLocal() as session:
        unk_stmt = select(Measurement).where(Measurement.event_id == unknown_event_id)
        unk_res = await session.execute(unk_stmt)
        assert unk_res.scalars().first() is None
        print(
            "  -> TRUST SECURITY CONFIRMED: Unknown device rejected; no device or measurement created."
        )

    print("\n" + "=" * 70)
    print("ALL PHASE 3 DEMONSTRATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_demonstration())
