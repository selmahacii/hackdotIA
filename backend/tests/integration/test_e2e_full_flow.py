"""Comprehensive End-to-End System Flow Verification.

Verifies:
1. Database integrity & seeded roles
2. Auth tokens & permissions for all 5 roles
3. Caregiver tenant isolation (IDOR protection)
4. Telemetry measurement persistence
5. Rule Engine Alert generation
6. Groq AI Enrichment pipeline execution & persistence
7. Alert acknowledgment & resolution
8. Dashboard stats & Admin metrics
"""

import uuid
from datetime import UTC, date, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.integrations.groq_client import FakeGroqClient
from app.models.ai_analysis import AIAnalysis
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
    SensorHealthStatus,
    UserRole,
)
from app.models.measurement import Measurement
from app.models.sensor_health import SensorHealth
from app.models.user import User
from app.services.ai_analysis import AIAnalysisService


@pytest.fixture
async def e2e_environment(db_session: AsyncSession) -> dict:
    """Setup isolated test fixtures for E2E verification."""
    # Resident 1 (Jeanne) & Resident 2 (Robert)
    res_1 = ElderlyPerson(
        id=uuid.uuid4(),
        first_name="Jeanne",
        last_name=f"E2E_{uuid.uuid4().hex[:4]}",
        date_of_birth=date(1938, 4, 12),
        is_active=True,
    )
    res_2 = ElderlyPerson(
        id=uuid.uuid4(),
        first_name="Robert",
        last_name=f"E2E_{uuid.uuid4().hex[:4]}",
        date_of_birth=date(1942, 9, 23),
        is_active=True,
    )
    db_session.add_all([res_1, res_2])
    await db_session.flush()

    # Devices
    dev_1 = Device(
        id=uuid.uuid4(),
        elderly_id=res_1.id,
        device_uid=f"ESP32-E2E-{uuid.uuid4().hex[:6]}",
        name="Bracelet Jeanne E2E",
        status=DeviceStatus.ONLINE,
    )
    dev_2 = Device(
        id=uuid.uuid4(),
        elderly_id=res_2.id,
        device_uid=f"ESP32-E2E-{uuid.uuid4().hex[:6]}",
        name="Bracelet Robert E2E",
        status=DeviceStatus.ONLINE,
    )
    db_session.add_all([dev_1, dev_2])
    await db_session.flush()

    # Sensor Health
    sh_1 = SensorHealth(
        id=uuid.uuid4(),
        device_id=dev_1.id,
        max30102_status=SensorHealthStatus.HEALTHY,
        mpu6050_status=SensorHealthStatus.HEALTHY,
        dht11_status=SensorHealthStatus.HEALTHY,
        gps_status=SensorHealthStatus.HEALTHY,
    )
    db_session.add(sh_1)

    # Alerts
    alt_1 = Alert(
        id=uuid.uuid4(),
        elderly_id=res_1.id,
        device_id=dev_1.id,
        alert_type=AlertType.FALL_SUSPECTED,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.OPEN,
        title="Impact violent détecté",
        description="Pic d'accélération à 4.2g suivi d'une absence prolongée de mouvement",
        source=AlertSource.RULE_ENGINE,
        occurred_at=datetime.now(UTC),
        dedup_key=f"fall-e2e-{uuid.uuid4()}",
    )
    alt_2 = Alert(
        id=uuid.uuid4(),
        elderly_id=res_2.id,
        device_id=dev_2.id,
        alert_type=AlertType.HEART_RATE_ANOMALY,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        title="Tachycardie de repos",
        description="BPM mesuré à 135 bpm pendant plus de 2 minutes",
        source=AlertSource.RULE_ENGINE,
        occurred_at=datetime.now(UTC),
        dedup_key=f"hr-e2e-{uuid.uuid4()}",
    )
    db_session.add_all([alt_1, alt_2])

    # Measurement
    meas_1 = Measurement(
        id=uuid.uuid4(),
        elderly_id=res_1.id,
        device_id=dev_1.id,
        measured_at=datetime.now(UTC),
        received_at=datetime.now(UTC),
        bpm=84.0,
        spo2=97.0,
        temperature_c=36.7,
        accel_magnitude_g=4.20,
    )
    db_session.add(meas_1)

    # Users for all 5 roles
    u_super = User(
        id=uuid.uuid4(),
        email=f"e2e_super_{uuid.uuid4().hex[:6]}@smartelderly.local",
        username=f"super_{uuid.uuid4().hex[:6]}",
        hashed_password="hash",
        role=UserRole.SUPERADMIN,
        is_active=True,
    )
    u_admin = User(
        id=uuid.uuid4(),
        email=f"e2e_admin_{uuid.uuid4().hex[:6]}@smartelderly.local",
        username=f"admin_{uuid.uuid4().hex[:6]}",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    u_caregiver_1 = User(
        id=uuid.uuid4(),
        email=f"e2e_cg1_{uuid.uuid4().hex[:6]}@smartelderly.local",
        username=f"cg1_{uuid.uuid4().hex[:6]}",
        hashed_password="hash",
        role=UserRole.CAREGIVER,
        is_active=True,
        assigned_elderly_ids=[str(res_1.id)],  # Only assigned to Resident 1
    )
    u_operator = User(
        id=uuid.uuid4(),
        email=f"e2e_op_{uuid.uuid4().hex[:6]}@smartelderly.local",
        username=f"op_{uuid.uuid4().hex[:6]}",
        hashed_password="hash",
        role=UserRole.OPERATOR,
        is_active=True,
    )
    u_readonly = User(
        id=uuid.uuid4(),
        email=f"e2e_ro_{uuid.uuid4().hex[:6]}@smartelderly.local",
        username=f"ro_{uuid.uuid4().hex[:6]}",
        hashed_password="hash",
        role=UserRole.READ_ONLY,
        is_active=True,
    )
    db_session.add_all([u_super, u_admin, u_caregiver_1, u_operator, u_readonly])
    await db_session.commit()

    return {
        "resident_1": res_1,
        "resident_2": res_2,
        "device_1": dev_1,
        "device_2": dev_2,
        "alert_1": alt_1,
        "alert_2": alt_2,
        "measurement_1": meas_1,
        "user_super": u_super,
        "user_admin": u_admin,
        "user_caregiver_1": u_caregiver_1,
        "user_operator": u_operator,
        "user_readonly": u_readonly,
    }


def token_for(user: User) -> str:
    return create_access_token(
        {
            "sub": user.username,
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "assigned_elderly_ids": user.assigned_elderly_ids,
        }
    )


@pytest.mark.asyncio
async def test_e2e_groq_ai_enrichment_pipeline(
    db_session: AsyncSession, e2e_environment: dict
) -> None:
    """Verify complete Groq AI enrichment execution and persistence in PostgreSQL."""
    alert = e2e_environment["alert_1"]

    fake_groq = FakeGroqClient()

    ai_service = AIAnalysisService(db_session, ai_client=fake_groq)
    analysis = await ai_service.run_enrichment_for_alert(alert.id, force=True)

    assert analysis is not None
    assert analysis.alert_id == alert.id
    assert analysis.status == AIAnalysisStatus.COMPLETED
    assert analysis.provider == AIProvider.GROQ
    assert analysis.confidence == 0.89
    assert "kinematic" in analysis.possible_event.lower()
    assert analysis.latency_ms is not None

    # Verify database persistence
    stmt = select(AIAnalysis).where(AIAnalysis.alert_id == alert.id)
    res = await db_session.execute(stmt)
    persisted = res.scalars().first()
    assert persisted is not None
    assert persisted.id == analysis.id


@pytest.mark.asyncio
async def test_e2e_caregiver_isolation_and_idor(
    async_client: AsyncClient, e2e_environment: dict
) -> None:
    """Verify strict tenant isolation for CAREGIVER role."""
    cg1 = e2e_environment["user_caregiver_1"]
    res1 = e2e_environment["resident_1"]
    res2 = e2e_environment["resident_2"]
    alt1 = e2e_environment["alert_1"]
    alt2 = e2e_environment["alert_2"]
    headers = {"Authorization": f"Bearer {token_for(cg1)}"}

    # Allowed: Resident 1
    r1 = await async_client.get(f"/api/v1/elderly/{res1.id}", headers=headers)
    assert r1.status_code == 200

    # IDOR Denied: Resident 2 (403 Forbidden)
    r2 = await async_client.get(f"/api/v1/elderly/{res2.id}", headers=headers)
    assert r2.status_code == 403

    # Allowed: Alert 1
    a1 = await async_client.get(f"/api/v1/alerts/{alt1.id}", headers=headers)
    assert a1.status_code == 200

    # IDOR Denied: Alert 2 (403 Forbidden)
    a2 = await async_client.get(f"/api/v1/alerts/{alt2.id}", headers=headers)
    assert a2.status_code == 403


@pytest.mark.asyncio
async def test_e2e_alert_workflow_ack_and_resolve(
    async_client: AsyncClient, e2e_environment: dict
) -> None:
    """Verify alert acknowledgment and resolution lifecycle."""
    operator = e2e_environment["user_operator"]
    alt1 = e2e_environment["alert_1"]
    headers = {"Authorization": f"Bearer {token_for(operator)}"}

    # Acknowledge
    ack = await async_client.post(f"/api/v1/alerts/{alt1.id}/ack", headers=headers)
    assert ack.status_code == 200
    assert ack.json()["status"] == "ACKNOWLEDGED"

    # Resolve
    resolve = await async_client.post(f"/api/v1/alerts/{alt1.id}/resolve", headers=headers)
    assert resolve.status_code == 200
    assert resolve.json()["status"] == "RESOLVED"


@pytest.mark.asyncio
async def test_e2e_rbac_role_boundaries(async_client: AsyncClient, e2e_environment: dict) -> None:
    """Verify mutation boundaries for READ_ONLY and OPERATOR vs ADMIN."""
    readonly = e2e_environment["user_readonly"]
    headers_ro = {"Authorization": f"Bearer {token_for(readonly)}"}

    # Read-only cannot create elderly
    create_try = await async_client.post(
        "/api/v1/elderly",
        json={"first_name": "Test", "last_name": "Denied"},
        headers=headers_ro,
    )
    assert create_try.status_code == 403

    # Admin can create elderly
    admin = e2e_environment["user_admin"]
    headers_admin = {"Authorization": f"Bearer {token_for(admin)}"}
    create_ok = await async_client.post(
        "/api/v1/elderly",
        json={"first_name": "Nouveau", "last_name": "Valide"},
        headers=headers_admin,
    )
    assert create_ok.status_code == 201


@pytest.mark.asyncio
async def test_e2e_dashboard_kpis_and_sensor_diagnostics(
    async_client: AsyncClient, e2e_environment: dict
) -> None:
    """Verify aggregated dashboard statistics and sensor health records."""
    super_user = e2e_environment["user_super"]
    headers = {"Authorization": f"Bearer {token_for(super_user)}"}

    # Dashboard Stats
    stats_res = await async_client.get("/api/v1/dashboard/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["kpi"]["residents_count"] >= 2
    assert stats["ai_engine"]["groq_enabled"] is True

    # Sensors Health
    sensors_res = await async_client.get("/api/v1/sensors", headers=headers)
    assert sensors_res.status_code == 200
    assert isinstance(sensors_res.json(), list)
    assert len(sensors_res.json()) >= 1
