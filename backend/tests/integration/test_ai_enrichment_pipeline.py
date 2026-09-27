"""Integration tests for AI Enrichment persistence and background pipeline."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.nvidia_client import FakeNVIDIAClient
from app.models.ai_analysis import AIAnalysis
from app.models.alert import Alert
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import (
    AIAnalysisStatus,
    AlertSeverity,
    AlertSource,
    AlertStatus,
    AlertType,
    DeviceStatus,
)
from app.models.measurement import Measurement
from app.services.ai_analysis import AIAnalysisService, run_enrichment_background


@pytest.mark.asyncio
async def test_full_ai_enrichment_pipeline_persistence(
    db_session: AsyncSession,
) -> None:
    # 1. Create resident and device
    elderly = ElderlyPerson(
        first_name="Marcelle",
        last_name="Gagnon",
        phone="+33633333333",
        is_active=True,
    )
    db_session.add(elderly)
    await db_session.flush()

    device = Device(
        device_uid=f"ESP32-E2E-{uuid.uuid4().hex[:8]}",
        name="Device Marcelle",
        elderly_id=elderly.id,
        status=DeviceStatus.ONLINE,
    )
    db_session.add(device)
    await db_session.flush()

    # 2. Ingest telemetry
    now = datetime.now(UTC)
    measurement = Measurement(
        event_id=uuid.uuid4(),
        device_id=device.id,
        elderly_id=elderly.id,
        received_at=now,
        measured_at=now,
        bpm=45.0,  # Bradycardia reading
        spo2=91.0,
        temperature_c=36.0,
        accel_magnitude_g=0.98,
        finger_detected=True,
        gps_fix_valid=True,
    )
    db_session.add(measurement)
    await db_session.flush()

    # 3. Create deterministic alert
    alert = Alert(
        id=uuid.uuid4(),
        elderly_id=elderly.id,
        device_id=device.id,
        alert_type=AlertType.HEART_RATE_ANOMALY,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        title="Heart Rate Anomaly Alert",
        description="Heart rate reading dropped below safety threshold",
        source=AlertSource.RULE_ENGINE,
        dedup_key=f"heart:{device.id}:{now.isoformat()}",
        context={"measurement_id": str(measurement.id)},
        created_at=now,
    )
    db_session.add(alert)
    await db_session.commit()

    # 4. Trigger enrichment via FakeNVIDIAClient
    fake_client = FakeNVIDIAClient()
    service = AIAnalysisService(db_session, ai_client=fake_client)
    analysis = await service.run_enrichment_for_alert(alert.id)

    # 5. Query from database to verify persistence
    stmt = select(AIAnalysis).where(AIAnalysis.id == analysis.id)
    result = await db_session.execute(stmt)
    persisted = result.scalar_one_or_none()

    assert persisted is not None
    assert persisted.alert_id == alert.id
    assert persisted.status == AIAnalysisStatus.COMPLETED
    assert persisted.confidence is not None and persisted.confidence > 0
    assert persisted.raw_response is not None
    assert persisted.completed_at is not None
    assert persisted.error is None


@pytest.mark.asyncio
async def test_run_enrichment_background(
    db_session: AsyncSession,
) -> None:
    # 1. Setup minimal alert
    elderly = ElderlyPerson(
        first_name="Pierre",
        last_name="Curie",
        phone="+33644444444",
        is_active=True,
    )
    db_session.add(elderly)
    await db_session.flush()

    device = Device(
        device_uid=f"ESP32-BG-{uuid.uuid4().hex[:8]}",
        name="Device Pierre",
        elderly_id=elderly.id,
        status=DeviceStatus.ONLINE,
    )
    db_session.add(device)
    await db_session.flush()

    now = datetime.now(UTC)
    alert = Alert(
        id=uuid.uuid4(),
        elderly_id=elderly.id,
        device_id=device.id,
        alert_type=AlertType.FALL_SUSPECTED,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.OPEN,
        title="Fall Suspected Alert",
        description="Sudden impact pattern detected",
        source=AlertSource.RULE_ENGINE,
        dedup_key=f"bg:fall:{uuid.uuid4()}",
        created_at=now,
    )
    db_session.add(alert)
    await db_session.commit()

    # 2. Run background enrichment with its own session
    fake_client = FakeNVIDIAClient()
    await run_enrichment_background(alert.id, ai_client=fake_client)

    # 3. Verify in test session
    stmt = select(AIAnalysis).where(AIAnalysis.alert_id == alert.id)
    result = await db_session.execute(stmt)
    persisted = result.scalar_one_or_none()

    assert persisted is not None
    assert persisted.status == AIAnalysisStatus.COMPLETED
    assert fake_client.call_count == 1
