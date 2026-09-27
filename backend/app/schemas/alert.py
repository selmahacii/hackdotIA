import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AlertSeverity, AlertSource, AlertStatus, AlertType
from app.schemas.common import ensure_utc_datetime, strip_non_empty_str


class AlertBase(BaseModel):
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.OPEN
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    source: AlertSource = AlertSource.RULE_ENGINE
    occurred_at: datetime
    occurrence_count: int = 1
    dedup_key: str = Field(..., min_length=1, max_length=255)
    context: dict[str, Any] | None = None

    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(cls, v: datetime) -> datetime:
        return ensure_utc_datetime(v)

    @field_validator("title", "description", "dedup_key")
    @classmethod
    def validate_strings(cls, v: str) -> str:
        return strip_non_empty_str(v)


class AlertCreate(AlertBase):
    elderly_id: uuid.UUID
    device_id: uuid.UUID | None = None

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: AlertSource) -> AlertSource:
        # Business rule: AI cannot be the primary origin of a physical alert
        if str(v).upper() == "AI":
            raise ValueError(
                "AI cannot be the primary source of an alert. Must be created via Rule Engine or Sensor Health."
            )
        return v


class AlertUpdate(BaseModel):
    """Restricted schema for updating mutable alert fields.

    Strictly forbids modifying immutable domain identifiers:
    elderly_id, device_id, alert_type, source, created_at.
    """

    model_config = ConfigDict(extra="forbid")

    status: AlertStatus | None = None
    severity: AlertSeverity | None = None
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = Field(default=None, max_length=100)
    resolved_at: datetime | None = None
    context: dict[str, Any] | None = None

    @field_validator("acknowledged_at", "resolved_at")
    @classmethod
    def validate_optional_timestamps(cls, v: datetime | None) -> datetime | None:
        if v is not None:
            return ensure_utc_datetime(v)
        return v


class AlertAcknowledgment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acknowledged_by: str = Field(..., min_length=1, max_length=100)
    acknowledged_at: datetime | None = None

    @field_validator("acknowledged_at")
    @classmethod
    def validate_ack_timestamp(cls, v: datetime | None) -> datetime | None:
        if v is not None:
            return ensure_utc_datetime(v)
        return v


class AlertResponse(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    elderly_id: uuid.UUID
    device_id: uuid.UUID | None = None
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
