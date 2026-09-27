"""Unit tests for AIAnalysisService, idempotency, and fallback behavior."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.nvidia_client import FakeNVIDIAClient
from app.models.alert import Alert
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import (
    AIAnalysisStatus,
    AIProvider,
    AlertSeverity,
    AlertSource,
    AlertStatus,
    AlertType,
    DeviceStatus,
)
from app.models.measurement import Measurement
from app.services.ai_analysis import AIAnalysisService


@pytest.fixture
async def sample_alert(db_session: AsyncSession) -> tuple[ElderlyPerson, Device, Alert]:
    elderly = ElderlyPerson(
        first_name="Jean",
        last_name="Dupont",
        phone="+33698765432",
        is_active=True,
    )
    db_session.add(elderly)
    await db_session.flush()

    device = Device(
        device_uid=f"ESP32-AI-{uuid.uuid4().hex[:8]}",
        name="Bracelet Jean",
        elderly_id=elderly.id,
        status=DeviceStatus.ONLINE,
    )
    db_session.add(device)
    await db_session.flush()

    now = datetime.now(UTC)
    measurement = Measurement(
        event_id=uuid.uuid4(),
        device_id=device.id,
        elderly_id=elderly.id,
        received_at=now,
        measured_at=now,
        bpm=125.0,
        spo2=95.0,
        temperature_c=37.1,
        humidity_percent=45.0,
        accel_x_g=0.1,
        accel_y_g=0.2,
        accel_z_g=2.9,
        accel_magnitude_g=2.91,
        finger_detected=True,
        gps_fix_valid=True,
        battery_level=90.0,
        wifi_rssi=-60,
    )
    db_session.add(measurement)
    await db_session.flush()

    alert = Alert(
        id=uuid.uuid4(),
        elderly_id=elderly.id,
        device_id=device.id,
        alert_type=AlertType.FALL_SUSPECTED,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.OPEN,
        title="Fall Suspected Alert",
        description="High acceleration spike detected",
        source=AlertSource.RULE_ENGINE,
        dedup_key=f"fall:{device.id}:{now.isoformat()}",
        context={"measurement_id": str(measurement.id)},
        created_at=now,
    )
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)

    return elderly, device, alert


@pytest.mark.asyncio
async def test_ai_analysis_service_successful_enrichment(
    db_session: AsyncSession,
    sample_alert: tuple[ElderlyPerson, Device, Alert],
) -> None:
    _, _, alert = sample_alert
    fake_client = FakeNVIDIAClient()
    service = AIAnalysisService(db_session, ai_client=fake_client)

    analysis = await service.run_enrichment_for_alert(alert.id)

    assert analysis.id is not None
    assert analysis.alert_id == alert.id
    assert analysis.status == AIAnalysisStatus.COMPLETED
    assert analysis.provider in (AIProvider.GROQ, AIProvider.NVIDIA)
    assert analysis.confidence == 0.88
    assert analysis.model_name == "meta/llama-3.1-8b-instruct"
    assert analysis.latency_ms == 42
    assert analysis.error is None
    assert "Kinematic anomaly" in (analysis.explanation or "")
    assert fake_client.call_count == 1


@pytest.mark.asyncio
async def test_ai_analysis_service_idempotency(
    db_session: AsyncSession,
    sample_alert: tuple[ElderlyPerson, Device, Alert],
) -> None:
    _, _, alert = sample_alert
    fake_client = FakeNVIDIAClient()
    service = AIAnalysisService(db_session, ai_client=fake_client)

    # First call
    analysis1 = await service.run_enrichment_for_alert(alert.id)
    assert fake_client.call_count == 1

    # Second call without force: must be idempotent and return existing record
    analysis2 = await service.run_enrichment_for_alert(alert.id, force=False)
    assert fake_client.call_count == 1  # Not incremented
    assert analysis1.id == analysis2.id

    # Third call with force=True: should re-trigger
    analysis3 = await service.run_enrichment_for_alert(alert.id, force=True)
    assert fake_client.call_count == 2
    assert analysis3.status == AIAnalysisStatus.COMPLETED


@pytest.mark.asyncio
async def test_ai_analysis_service_timeout_fallback(
    db_session: AsyncSession,
    sample_alert: tuple[ElderlyPerson, Device, Alert],
) -> None:
    _, _, alert = sample_alert
    fake_client = FakeNVIDIAClient(simulate_timeout=True)
    service = AIAnalysisService(db_session, ai_client=fake_client)

    analysis = await service.run_enrichment_for_alert(alert.id, force=True)

    # Must gracefully fall back without crashing or rolling back the alert
    assert analysis.status == AIAnalysisStatus.FALLBACK
    assert analysis.provider == AIProvider.FALLBACK_RULES
    assert analysis.error is not None
    assert "timeout" in analysis.error.lower()
    assert analysis.confidence == 0.70
    assert analysis.explanation is not None

    # Verify underlying alert is still intact and open
    await db_session.refresh(alert)
    assert alert.status == AlertStatus.OPEN


@pytest.mark.asyncio
async def test_ai_analysis_service_nvidia_disabled(
    db_session: AsyncSession,
    sample_alert: tuple[ElderlyPerson, Device, Alert],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "GROQ_ENABLED", False)
    monkeypatch.setattr(settings, "NVIDIA_ENABLED", False)
    _, _, alert = sample_alert
    service = AIAnalysisService(db_session, ai_client=None)

    analysis = await service.run_enrichment_for_alert(alert.id, force=True)

    assert analysis.status == AIAnalysisStatus.FALLBACK
    assert analysis.provider == AIProvider.FALLBACK_RULES
    assert (
        "disabled"
        in (analysis.raw_response.get("context", "") if analysis.raw_response else "").lower()
    )
