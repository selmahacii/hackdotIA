"""Integration tests for AI Analysis API endpoints, authentication, and RBAC."""

from datetime import UTC, datetime
import uuid

from httpx import AsyncClient
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.alert import Alert
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import AlertSeverity, AlertSource, AlertStatus, AlertType, DeviceStatus
from app.models.measurement import Measurement
from app.services.ai_analysis import AIAnalysisService


@pytest.fixture
async def rbac_test_data(
    db_session: AsyncSession,
) -> tuple[ElderlyPerson, ElderlyPerson, Device, Alert]:
    elderly1 = ElderlyPerson(
        first_name="Alice",
        last_name="Martin",
        phone="+33611111111",
        is_active=True,
    )
    elderly2 = ElderlyPerson(
        first_name="Bob",
        last_name="Bernard",
        phone="+33622222222",
        is_active=True,
    )
    db_session.add_all([elderly1, elderly2])
    await db_session.flush()

    device = Device(
        device_uid=f"ESP32-RBAC-{uuid.uuid4().hex[:8]}",
        name="Device Alice",
        elderly_id=elderly1.id,
        status=DeviceStatus.ONLINE,
    )
    db_session.add(device)
    await db_session.flush()

    now = datetime.now(UTC)
    meas = Measurement(
        event_id=uuid.uuid4(),
        device_id=device.id,
        elderly_id=elderly1.id,
        received_at=now,
        measured_at=now,
        bpm=130.0,
        spo2=94.0,
        temperature_c=37.0,
        accel_magnitude_g=3.1,
    )
    db_session.add(meas)
    await db_session.flush()

    alert = Alert(
        id=uuid.uuid4(),
        elderly_id=elderly1.id,
        device_id=device.id,
        alert_type=AlertType.FALL_SUSPECTED,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.OPEN,
        title="Fall Suspected Alert",
        description="High acceleration spike detected",
        source=AlertSource.RULE_ENGINE,
        dedup_key=f"rbac:alert:{uuid.uuid4()}",
        context={"measurement_id": str(meas.id)},
        created_at=now,
    )
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)

    return elderly1, elderly2, device, alert


def auth_header(
    role: str, user_id: str = "test-user", assigned_ids: list[str] | None = None
) -> dict[str, str]:
    payload = {
        "sub": user_id,
        "role": role,
        "assigned_elderly_ids": assigned_ids or [],
    }
    token = create_access_token(payload)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_analysis_missing_and_invalid_auth(
    async_client: AsyncClient,
    rbac_test_data: tuple[ElderlyPerson, ElderlyPerson, Device, Alert],
) -> None:
    _, _, _, alert = rbac_test_data

    # No auth header -> 401
    resp = await async_client.get(f"/api/v1/alerts/{alert.id}/ai-analysis")
    assert resp.status_code == 401

    # Invalid token -> 401
    resp = await async_client.get(
        f"/api/v1/alerts/{alert.id}/ai-analysis",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_analysis_not_found(
    async_client: AsyncClient,
    rbac_test_data: tuple[ElderlyPerson, ElderlyPerson, Device, Alert],
) -> None:
    _, _, _, alert = rbac_test_data

    # Alert exists but no analysis triggered yet -> 404
    resp = await async_client.get(
        f"/api/v1/alerts/{alert.id}/ai-analysis",
        headers=auth_header("ADMIN"),
    )
    assert resp.status_code == 404
    assert "No AI analysis found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_post_trigger_rbac_forbidden_for_read_only(
    async_client: AsyncClient,
    rbac_test_data: tuple[ElderlyPerson, ElderlyPerson, Device, Alert],
) -> None:
    _, _, _, alert = rbac_test_data

    # READ_ONLY user attempting to trigger analysis -> 403 Forbidden
    resp = await async_client.post(
        f"/api/v1/alerts/{alert.id}/ai-analysis",
        headers=auth_header("READ_ONLY"),
    )
    assert resp.status_code == 403
    assert "Operation not permitted" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_post_trigger_and_get_analysis_admin(
    async_client: AsyncClient,
    rbac_test_data: tuple[ElderlyPerson, ElderlyPerson, Device, Alert],
) -> None:
    _, _, _, alert = rbac_test_data

    # Trigger analysis as ADMIN
    resp_post = await async_client.post(
        f"/api/v1/alerts/{alert.id}/ai-analysis",
        headers=auth_header("ADMIN"),
    )
    assert resp_post.status_code == 200
    data = resp_post.json()
    assert data["alert_id"] == str(alert.id)
    assert data["status"] in ("COMPLETED", "FALLBACK")
    assert data["confidence"] is not None

    # Get analysis as ADMIN
    resp_get = await async_client.get(
        f"/api/v1/alerts/{alert.id}/ai-analysis",
        headers=auth_header("ADMIN"),
    )
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == data["id"]


@pytest.mark.asyncio
async def test_caregiver_assigned_elderly_isolation(
    async_client: AsyncClient,
    rbac_test_data: tuple[ElderlyPerson, ElderlyPerson, Device, Alert],
) -> None:
    elderly1, elderly2, _, alert1 = rbac_test_data

    # Caregiver assigned ONLY to elderly2 attempts to access alert of elderly1 -> 403 Forbidden
    unauthorized_headers = auth_header("CAREGIVER", assigned_ids=[str(elderly2.id)])
    resp = await async_client.get(
        f"/api/v1/alerts/{alert1.id}/ai-analysis",
        headers=unauthorized_headers,
    )
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"]

    # Caregiver assigned to elderly1 succeeds
    authorized_headers = auth_header("CAREGIVER", assigned_ids=[str(elderly1.id)])
    resp_auth = await async_client.post(
        f"/api/v1/alerts/{alert1.id}/ai-analysis",
        headers=authorized_headers,
    )
    assert resp_auth.status_code == 200
