import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import AlertSeverity, AlertSource, AlertStatus, AlertType, DeviceStatus


@pytest.mark.asyncio
async def test_duplicate_device_uid_fails(db_session: AsyncSession) -> None:
    elderly = ElderlyPerson(first_name="Jean", last_name="Dupont")
    db_session.add(elderly)
    await db_session.flush()

    shared_uid = f"SHARED-UID-{uuid.uuid4().hex[:6]}"
    d1 = Device(
        device_uid=shared_uid,
        elderly_id=elderly.id,
        status=DeviceStatus.ONLINE,
    )
    db_session.add(d1)
    await db_session.flush()

    d2 = Device(
        device_uid=shared_uid,
        elderly_id=elderly.id,
        status=DeviceStatus.OFFLINE,
    )
    db_session.add(d2)

    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_duplicate_active_dedup_key_fails(db_session: AsyncSession) -> None:
    elderly = ElderlyPerson(first_name="Marie", last_name="Curie")
    db_session.add(elderly)
    await db_session.flush()

    dedup = f"{elderly.id}:FALL_ACTIVE_TEST"
    now = datetime.now(UTC)

    # First active alert (OPEN)
    a1 = Alert(
        elderly_id=elderly.id,
        alert_type=AlertType.FALL_SUSPECTED,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        title="Première alerte active",
        description="Chute suspectée",
        source=AlertSource.RULE_ENGINE,
        occurred_at=now,
        dedup_key=dedup,
    )
    db_session.add(a1)
    await db_session.flush()

    # Second active alert (ACKNOWLEDGED is also active) with SAME dedup_key
    a2 = Alert(
        elderly_id=elderly.id,
        alert_type=AlertType.FALL_SUSPECTED,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.ACKNOWLEDGED,
        title="Deuxième alerte active en doublon",
        description="Même chute suspectée",
        source=AlertSource.RULE_ENGINE,
        occurred_at=now,
        dedup_key=dedup,
    )
    db_session.add(a2)

    # Must fail because of partial unique index uq_alert_active_dedup_key
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_duplicate_resolved_dedup_key_allowed(db_session: AsyncSession) -> None:
    elderly = ElderlyPerson(first_name="Paul", last_name="Valery")
    db_session.add(elderly)
    await db_session.flush()

    dedup = f"{elderly.id}:FALL_RESOLVED_TEST"
    now = datetime.now(UTC)

    # 1. Past resolved alert (RESOLVED)
    a1 = Alert(
        elderly_id=elderly.id,
        alert_type=AlertType.FALL_SUSPECTED,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.RESOLVED,
        title="Ancienne alerte résolue",
        description="Événement clôturé",
        source=AlertSource.RULE_ENGINE,
        occurred_at=now,
        resolved_at=now,
        dedup_key=dedup,
    )
    db_session.add(a1)
    await db_session.flush()
    assert a1.id is not None

    # 2. New active alert (OPEN) with SAME dedup_key must be ALLOWED!
    a2 = Alert(
        elderly_id=elderly.id,
        alert_type=AlertType.FALL_SUSPECTED,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        title="Nouvelle alerte active récurrente",
        description="Nouvel événement",
        source=AlertSource.RULE_ENGINE,
        occurred_at=now,
        dedup_key=dedup,
    )
    db_session.add(a2)
    await db_session.flush()
    assert a2.id is not None
    assert a1.id != a2.id
