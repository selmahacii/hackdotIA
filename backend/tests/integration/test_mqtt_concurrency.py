import asyncio
import uuid

import pytest
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import DeviceStatus
from app.models.measurement import Measurement
from app.mqtt.errors import DuplicateEventError
from app.mqtt.service import MQTTIngestionService


@pytest.mark.asyncio
async def test_concurrent_duplicate_events_guarantee_single_insertion() -> None:
    """
    Critical concurrency test:
    10 simultaneous ingestion requests with the same event_id must result in
    EXACTLY ONE persisted Measurement, with all 9 other attempts cleanly
    identified as duplicates without database corruption or unhandled errors.
    """
    device_uid = f"ESP32-CONCURRENCY-{uuid.uuid4().hex[:8]}"

    # Setup device and elderly person
    async with AsyncSessionLocal() as setup_session:
        elderly = ElderlyPerson(
            first_name="Hélène",
            last_name="Martin",
            phone="+33698765432",
            is_active=True,
        )
        setup_session.add(elderly)
        await setup_session.flush()

        device = Device(
            device_uid=device_uid,
            name="Bracelet Concurrence",
            elderly_id=elderly.id,
            status=DeviceStatus.UNKNOWN,
        )
        setup_session.add(device)
        await setup_session.commit()

    shared_event_id = uuid.uuid4()
    payload = {
        "schema_version": "1.0",
        "event_id": str(shared_event_id),
        "device_uid": device_uid,
        "timestamp": "2026-09-27T10:30:00Z",
        "finger_detected": True,
        "bpm": 76.0,
        "spo2": 97.0,
        "temperature_c": 21.8,
        "humidity_percent": 50.0,
        "accel_x_g": 0.01,
        "accel_y_g": 0.02,
        "accel_z_g": 0.98,
        "accel_magnitude_g": 0.98,
        "battery_level": 80,
        "wifi_rssi": -65,
    }

    async def ingest_attempt(attempt_idx: int) -> str:
        async with AsyncSessionLocal() as session:
            service = MQTTIngestionService(session)
            try:
                await service.ingest_telemetry(payload, topic_device_uid=device_uid)
                return "SUCCESS"
            except DuplicateEventError:
                return "DUPLICATE"

    # Launch 10 concurrent ingestion attempts simultaneously
    tasks = [ingest_attempt(i) for i in range(10)]
    results = await asyncio.gather(*tasks)

    success_count = results.count("SUCCESS")
    duplicate_count = results.count("DUPLICATE")

    assert success_count == 1, f"Expected exactly 1 success, got {success_count}"
    assert duplicate_count == 9, f"Expected exactly 9 duplicates, got {duplicate_count}"

    # Verify database state
    async with AsyncSessionLocal() as verify_session:
        count_stmt = select(func.count(Measurement.id)).where(
            Measurement.event_id == shared_event_id
        )
        count_result = await verify_session.execute(count_stmt)
        persisted_count = count_result.scalar_one()

        assert (
            persisted_count == 1
        ), f"Database has {persisted_count} measurements for event_id, expected 1"
