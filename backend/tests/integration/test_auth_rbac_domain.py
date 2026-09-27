"""Integration tests for Auth, RBAC roles, Caregiver isolation, and Domain APIs."""

import uuid
from datetime import UTC, date, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.alert import Alert
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import (
    AlertSeverity,
    AlertSource,
    AlertStatus,
    AlertType,
    DeviceStatus,
    UserRole,
)
from app.models.measurement import Measurement
from app.models.user import User


@pytest.fixture
async def setup_rbac_env(db_session: AsyncSession) -> dict:
    """Create test residents, devices, alerts, and users for RBAC testing."""
    # Resident A & B
    e1 = ElderlyPerson(
        id=uuid.uuid4(),
        first_name="Jeanne",
        last_name="TestA",
        date_of_birth=date(1935, 1, 1),
        is_active=True,
    )
    e2 = ElderlyPerson(
        id=uuid.uuid4(),
        first_name="Robert",
        last_name="TestB",
        date_of_birth=date(1940, 5, 10),
        is_active=True,
    )
    db_session.add_all([e1, e2])
    await db_session.flush()

    # Devices
    uid_a = f"DEV-A-{uuid.uuid4().hex[:8]}"
    uid_b = f"DEV-B-{uuid.uuid4().hex[:8]}"
    d1 = Device(
        id=uuid.uuid4(),
        elderly_id=e1.id,
        device_uid=uid_a,
        name="Device A",
        status=DeviceStatus.ONLINE,
    )
    d2 = Device(
        id=uuid.uuid4(),
        elderly_id=e2.id,
        device_uid=uid_b,
        name="Device B",
        status=DeviceStatus.ONLINE,
    )
    db_session.add_all([d1, d2])
    await db_session.flush()

    # Alerts
    a1 = Alert(
        id=uuid.uuid4(),
        elderly_id=e1.id,
        device_id=d1.id,
        alert_type=AlertType.FALL_SUSPECTED,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.OPEN,
        title="Chute suspectée Résident A",
        description="Forte accélération",
        source=AlertSource.RULE_ENGINE,
        occurred_at=datetime.now(UTC),
        dedup_key=f"fall-test-a-{uuid.uuid4()}",
    )
    a2 = Alert(
        id=uuid.uuid4(),
        elderly_id=e2.id,
        device_id=d2.id,
        alert_type=AlertType.HEART_RATE_ANOMALY,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        title="Tachycardie Résident B",
        description="BPM élevé",
        source=AlertSource.RULE_ENGINE,
        occurred_at=datetime.now(UTC),
        dedup_key=f"hr-test-b-{uuid.uuid4()}",
    )
    db_session.add_all([a1, a2])

    # Measurement
    m1 = Measurement(
        id=uuid.uuid4(),
        elderly_id=e1.id,
        device_id=d1.id,
        measured_at=datetime.now(UTC),
        received_at=datetime.now(UTC),
        bpm=78.0,
        spo2=98.0,
        temperature_c=36.8,
        accel_magnitude_g=1.02,
    )
    db_session.add(m1)

    # Test Users
    rand_super = uuid.uuid4().hex[:6]
    rand_cg = uuid.uuid4().hex[:6]
    rand_ro = uuid.uuid4().hex[:6]

    u_super = User(
        id=uuid.uuid4(),
        email=f"test_super_{rand_super}@example.com",
        username=f"tsuper_{rand_super}",
        hashed_password=hash_password("SuperSecret1!"),
        role=UserRole.SUPERADMIN,
        is_active=True,
    )
    u_caregiver_a = User(
        id=uuid.uuid4(),
        email=f"test_caregiver_a_{rand_cg}@example.com",
        username=f"tcaregiver_{rand_cg}",
        hashed_password=hash_password("Caregiver1!"),
        role=UserRole.CAREGIVER,
        is_active=True,
        assigned_elderly_ids=[str(e1.id)],  # Only assigned to Resident A!
    )
    u_readonly = User(
        id=uuid.uuid4(),
        email=f"test_readonly_{rand_ro}@example.com",
        username=f"treadonly_{rand_ro}",
        hashed_password=hash_password("ReadOnly1!"),
        role=UserRole.READ_ONLY,
        is_active=True,
    )
    db_session.add_all([u_super, u_caregiver_a, u_readonly])
    await db_session.commit()

    return {
        "resident_a": e1,
        "resident_b": e2,
        "device_a": d1,
        "device_b": d2,
        "alert_a": a1,
        "alert_b": a2,
        "measurement_a": m1,
        "user_super": u_super,
        "user_caregiver_a": u_caregiver_a,
        "user_readonly": u_readonly,
    }


def make_token(user: User) -> str:
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
async def test_auth_login_success_and_failure(
    async_client: AsyncClient, setup_rbac_env: dict
) -> None:
    u = setup_rbac_env["user_super"]

    # Valid login
    res = await async_client.post(
        "/api/v1/auth/login",
        json={"username": u.username, "password": "SuperSecret1!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["username"] == u.username
    assert data["user"]["role"] == "SUPERADMIN"

    # Invalid password
    res_bad = await async_client.post(
        "/api/v1/auth/login",
        json={"username": u.username, "password": "WrongPassword!"},
    )
    assert res_bad.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_endpoint(async_client: AsyncClient, setup_rbac_env: dict) -> None:
    u = setup_rbac_env["user_caregiver_a"]
    token = make_token(u)

    res = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == u.username
    assert data["role"] == "CAREGIVER"
    assert len(data["assigned_elderly_ids"]) == 1


@pytest.mark.asyncio
async def test_caregiver_tenant_isolation_idor(
    async_client: AsyncClient, setup_rbac_env: dict
) -> None:
    caregiver = setup_rbac_env["user_caregiver_a"]
    alert_a = setup_rbac_env["alert_a"]
    alert_b = setup_rbac_env["alert_b"]
    res_a = setup_rbac_env["resident_a"]
    res_b = setup_rbac_env["resident_b"]
    token = make_token(caregiver)
    headers = {"Authorization": f"Bearer {token}"}

    # Caregiver can access Resident A
    res = await async_client.get(f"/api/v1/elderly/{res_a.id}", headers=headers)
    assert res.status_code == 200

    # IDOR Check: Caregiver CANNOT access Resident B (403 Forbidden)
    res_idor = await async_client.get(f"/api/v1/elderly/{res_b.id}", headers=headers)
    assert res_idor.status_code == 403

    # Caregiver can access Alert A
    res = await async_client.get(f"/api/v1/alerts/{alert_a.id}", headers=headers)
    assert res.status_code == 200

    # IDOR Check: Caregiver CANNOT access Alert B (403 Forbidden)
    res_idor_alert = await async_client.get(f"/api/v1/alerts/{alert_b.id}", headers=headers)
    assert res_idor_alert.status_code == 403


@pytest.mark.asyncio
async def test_alert_ack_and_resolve(async_client: AsyncClient, setup_rbac_env: dict) -> None:
    caregiver = setup_rbac_env["user_caregiver_a"]
    alert_a = setup_rbac_env["alert_a"]
    token = make_token(caregiver)
    headers = {"Authorization": f"Bearer {token}"}

    # Acknowledge Alert A
    ack_res = await async_client.post(f"/api/v1/alerts/{alert_a.id}/ack", headers=headers)
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "ACKNOWLEDGED"

    # Resolve Alert A
    resolve_res = await async_client.post(f"/api/v1/alerts/{alert_a.id}/resolve", headers=headers)
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "RESOLVED"


@pytest.mark.asyncio
async def test_readonly_user_cannot_mutate(async_client: AsyncClient, setup_rbac_env: dict) -> None:
    readonly_user = setup_rbac_env["user_readonly"]
    alert_a = setup_rbac_env["alert_a"]
    token = make_token(readonly_user)
    headers = {"Authorization": f"Bearer {token}"}

    # Read-only user CAN view alerts
    res_view = await async_client.get(f"/api/v1/alerts/{alert_a.id}", headers=headers)
    assert res_view.status_code == 200

    # Read-only user CANNOT acknowledge alerts (403)
    res_ack = await async_client.post(f"/api/v1/alerts/{alert_a.id}/ack", headers=headers)
    assert res_ack.status_code == 403

    # Read-only user CANNOT create elderly residents (403)
    res_create = await async_client.post(
        "/api/v1/elderly",
        json={"first_name": "Test", "last_name": "ReadonlyBlock"},
        headers=headers,
    )
    assert res_create.status_code == 403


@pytest.mark.asyncio
async def test_dashboard_and_measurements_apis(
    async_client: AsyncClient, setup_rbac_env: dict
) -> None:
    super_user = setup_rbac_env["user_super"]
    token = make_token(super_user)
    headers = {"Authorization": f"Bearer {token}"}

    # Dashboard stats
    dash_res = await async_client.get("/api/v1/dashboard/stats", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "kpi" in dash_data
    assert dash_data["kpi"]["residents_count"] >= 2
    assert dash_data["ai_engine"]["groq_enabled"] is True

    # Measurements list
    m_res = await async_client.get("/api/v1/measurements", headers=headers)
    assert m_res.status_code == 200
    assert isinstance(m_res.json(), list)

    # Admin stats
    admin_stats = await async_client.get("/api/v1/admin/stats", headers=headers)
    assert admin_stats.status_code == 200
    assert admin_stats.json()["system_status"] == "OPERATIONAL"
