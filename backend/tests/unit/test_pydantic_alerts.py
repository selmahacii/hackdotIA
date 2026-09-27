import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.enums import AlertSeverity, AlertSource, AlertStatus, AlertType
from app.schemas.alert import AlertAcknowledgment, AlertCreate, AlertUpdate


def test_alert_create_valid() -> None:
    now = datetime.now(UTC)
    alert = AlertCreate(
        elderly_id=uuid.uuid4(),
        alert_type=AlertType.FALL_SUSPECTED,
        severity=AlertSeverity.CRITICAL,
        title="Chute détectée",
        description="Forte décélération suivie d'inactivité.",
        source=AlertSource.RULE_ENGINE,
        occurred_at=now,
        dedup_key="elderly_1:FALL_SUSPECTED",
    )
    assert alert.alert_type == AlertType.FALL_SUSPECTED
    assert alert.source == AlertSource.RULE_ENGINE


def test_alert_create_cannot_set_ai_source() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError) as exc:
        AlertCreate(
            elderly_id=uuid.uuid4(),
            alert_type=AlertType.FALL_SUSPECTED,
            severity=AlertSeverity.HIGH,
            title="Alerte",
            description="Description",
            source="AI",  # type: ignore[arg-type]
            occurred_at=now,
            dedup_key="key",
        )
    assert "Input should be 'RULE_ENGINE'" in str(
        exc.value
    ) or "AI cannot be the primary source" in str(exc.value)


def test_alert_update_immutable_fields_rejected() -> None:
    # Attempting to mutate immutable fields must fail due to extra="forbid"
    with pytest.raises(ValidationError) as exc:
        AlertUpdate(
            elderly_id=uuid.uuid4(),  # type: ignore[call-arg]
        )
    assert "extra_forbidden" in str(exc.value) or "Extra inputs are not permitted" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        AlertUpdate(
            device_id=uuid.uuid4(),  # type: ignore[call-arg]
        )
    assert "extra_forbidden" in str(exc.value) or "Extra inputs are not permitted" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        AlertUpdate(
            alert_type=AlertType.HEART_RATE_ANOMALY,  # type: ignore[call-arg]
        )
    assert "extra_forbidden" in str(exc.value) or "Extra inputs are not permitted" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        AlertUpdate(
            source=AlertSource.DEVICE,  # type: ignore[call-arg]
        )
    assert "extra_forbidden" in str(exc.value) or "Extra inputs are not permitted" in str(exc.value)


def test_alert_update_mutable_fields_accepted() -> None:
    now = datetime.now(UTC)
    update = AlertUpdate(
        status=AlertStatus.ACKNOWLEDGED,
        acknowledged_at=now,
        acknowledged_by="Infirmière Sarah",
        context={"note": "Prise en charge en cours"},
    )
    assert update.status == AlertStatus.ACKNOWLEDGED
    assert update.acknowledged_by == "Infirmière Sarah"


def test_alert_acknowledgment() -> None:
    now = datetime.now(UTC)
    ack = AlertAcknowledgment(
        acknowledged_by="Dr. Bensaid",
        acknowledged_at=now,
    )
    assert ack.acknowledged_by == "Dr. Bensaid"

    # Cannot be empty string
    with pytest.raises(ValidationError):
        AlertAcknowledgment(acknowledged_by="")
