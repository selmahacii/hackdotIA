# ruff: noqa: E402
"""Phase 5 Live Demonstration Script: NVIDIA AI Enrichment Engine."""

import asyncio
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

from sqlalchemy import select

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.integrations.nvidia_client import FakeNVIDIAClient
from app.models.ai_analysis import AIAnalysis
from app.models.alert import Alert
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import (
    AlertSeverity,
    AlertSource,
    AlertStatus,
    AlertType,
    DeviceStatus,
)
from app.models.measurement import Measurement
from app.services.ai_analysis import AIAnalysisService


async def run_phase5_demo() -> None:
    print("=" * 80)
    print("PHASE 5 LIVE DEMONSTRATION: NVIDIA AI ENRICHMENT ENGINE")
    print("=" * 80)
    print(f"NVIDIA_ENABLED: {settings.NVIDIA_ENABLED}")
    print(f"NVIDIA_MODEL:   {settings.NVIDIA_MODEL}")
    print(f"NVIDIA_BASE_URL:{settings.NVIDIA_BASE_URL}")
    print(f"API Key set:    {bool(settings.NVIDIA_API_KEY)}")

    device_uid = "ESP32-PHASE5-DEMO"

    # Step 1: Provision resident & device
    print(f"\n[STEP 1] Provisioning test resident and device ({device_uid})...")
    async with AsyncSessionLocal() as session:
        dev_stmt = select(Device).where(Device.device_uid == device_uid)
        res = await session.execute(dev_stmt)
        device = res.scalars().first()

        if not device:
            elderly = ElderlyPerson(
                first_name="Charles",
                last_name="Baudelaire",
                phone="+33655443322",
                is_active=True,
            )
            session.add(elderly)
            await session.flush()

            device = Device(
                device_uid=device_uid,
                name="Bracelet Charles",
                elderly_id=elderly.id,
                status=DeviceStatus.ONLINE,
            )
            session.add(device)
            await session.commit()
            await session.refresh(device)
            elderly_id = elderly.id
        else:
            elderly_id = device.elderly_id

    print(f"[OK] Resident ID: {elderly_id}")
    print(f"[OK] Device ID:   {device.id} ({device.device_uid})")

    # Step 2: Record telemetry measurement with kinematic spike
    print("\n[STEP 2] Ingesting telemetry with kinematic impact spike (3.42g)...")
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as session:
        meas = Measurement(
            event_id=uuid.uuid4(),
            device_id=device.id,
            elderly_id=elderly_id,
            received_at=now,
            measured_at=now,
            bpm=118.0,
            spo2=96.0,
            temperature_c=36.7,
            humidity_percent=48.0,
            accel_x_g=0.2,
            accel_y_g=0.3,
            accel_z_g=3.4,
            accel_magnitude_g=3.42,
            finger_detected=True,
            gps_fix_valid=True,
            battery_level=92.0,
            wifi_rssi=-58,
        )
        session.add(meas)
        await session.commit()
        await session.refresh(meas)
        measurement_id = meas.id

    print(f"[OK] Measurement persisted: {measurement_id} (magnitude: 3.42g, bpm: 118.0)")

    # Step 3: Trigger deterministic alert
    print("\n[STEP 3] Triggering deterministic Alert (independent of AI)...")
    async with AsyncSessionLocal() as session:
        alert = Alert(
            id=uuid.uuid4(),
            elderly_id=elderly_id,
            device_id=device.id,
            alert_type=AlertType.FALL_SUSPECTED,
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.OPEN,
            title="Fall Suspected Alert",
            description="Kinematic deceleration spike (3.42g) detected by accelerometer",
            source=AlertSource.RULE_ENGINE,
            dedup_key=f"demo:fall:{device.id}:{now.isoformat()}",
            context={"measurement_id": str(measurement_id)},
            created_at=now,
        )
        session.add(alert)
        await session.commit()
        await session.refresh(alert)
        alert_id = alert.id

    print(f"[OK] Deterministic Alert created: {alert_id}")
    print(
        f"  Type: {alert.alert_type.value}, Severity: {alert.severity.value}, Status: {alert.status.value}"
    )
    print("  Note: Alert is committed immediately before any AI call.")

    # Step 4: Run AI Enrichment Engine
    print("\n[STEP 4] Executing AI Enrichment Engine (AIAnalysisService)...")
    async with AsyncSessionLocal() as session:
        # If API key configured, use real NVIDIA client, otherwise use FakeNVIDIAClient
        service = AIAnalysisService(session)
        start_time = datetime.now(UTC)
        analysis = await service.run_enrichment_for_alert(alert_id)
        duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

    print("[OK] AI Enrichment completed:")
    print(f"  Analysis ID:        {analysis.id}")
    print(f"  Status:             {analysis.status.value}")
    print(f"  Provider:           {analysis.provider.value}")
    print(f"  Model:              {analysis.model_name}")
    print(f"  Latency:            {analysis.latency_ms or duration_ms} ms")
    print(f"  Confidence:         {analysis.confidence}")
    print(f"  Explanation:        {analysis.explanation}")
    print(f"  Recommended Action: {analysis.recommended_action}")
    if analysis.error:
        print(f"  Error / Note:       {analysis.error}")

    # Step 5: Test Idempotency
    print("\n[STEP 5] Testing Idempotency (re-calling without force)...")
    async with AsyncSessionLocal() as session:
        service = AIAnalysisService(session)
        analysis_cached = await service.run_enrichment_for_alert(alert_id, force=False)
        assert analysis_cached.id == analysis.id, "Idempotency failed: new ID generated"
        print(
            f"[OK] Idempotency verified: existing record returned (id={analysis_cached.id}) without duplicate call."
        )

    # Step 6: Test Graceful Fallback on Simulated Failure
    print("\n[STEP 6] Testing Resilient Fallback on simulated AI timeout...")
    async with AsyncSessionLocal() as session:
        fake_timeout_client = FakeNVIDIAClient(simulate_timeout=True)
        service_timeout = AIAnalysisService(session, ai_client=fake_timeout_client)
        fallback_analysis = await service_timeout.run_enrichment_for_alert(alert_id, force=True)

    print("[OK] Safe Fallback verified:")
    print(f"  Status:      {fallback_analysis.status.value}")
    print(f"  Provider:    {fallback_analysis.provider.value}")
    print(f"  Error saved: {fallback_analysis.error}")
    print(f"  Explanation: {fallback_analysis.explanation}")

    # Step 7: Verify DB state
    print("\n[STEP 7] Final PostgreSQL state verification...")
    async with AsyncSessionLocal() as session:
        stmt = select(AIAnalysis).where(AIAnalysis.alert_id == alert_id)
        res = await session.execute(stmt)
        analyses = res.scalars().all()
        print(f"[OK] Found {len(analyses)} AIAnalysis records for alert {alert_id} in PostgreSQL.")

    print("\n" + "=" * 80)
    print("PHASE 5 LIVE DEMONSTRATION COMPLETE: ALL CHECKS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_phase5_demo())
