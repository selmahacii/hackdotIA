import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AIAnalysisStatus, AIProvider
from app.schemas.common import ensure_utc_datetime


class AIAnalysisBase(BaseModel):
    provider: AIProvider = AIProvider.NVIDIA
    status: AIAnalysisStatus = AIAnalysisStatus.PENDING
    risk_level: str | None = Field(default=None, max_length=50)
    anomaly_detected: bool | None = None
    possible_event: str | None = Field(default=None, max_length=100)
    explanation: str | None = Field(
        default=None,
        max_length=500,
        description="Factual summary of detected anomaly; must not contain medical diagnosis.",
    )
    recommended_action: str | None = Field(
        default=None,
        max_length=500,
        description="Recommended operational check or next step.",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="System confidence indicator between 0.0 and 1.0; not a medical probability.",
    )
    model_name: str | None = Field(default=None, max_length=100)
    latency_ms: int | None = Field(default=None, ge=0)
    error: str | None = Field(default=None, description="Error message if analysis failed")


class AIEnrichmentResult(BaseModel):
    summary: str = Field(
        ..., min_length=1, max_length=500, description="Factual, non-medical summary of the event"
    )
    observations: list[str] = Field(default_factory=list, description="Key sensor observations")
    context: str = Field(
        default="", max_length=500, description="Environmental or sensor trend context"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="System confidence indicator between 0.0 and 1.0"
    )
    data_quality: str = Field(
        default="UNKNOWN", max_length=50, description="Sensor data quality indicator"
    )
    possible_factors: list[str] = Field(
        default_factory=list, description="Possible non-medical factors"
    )
    recommended_checks: list[str] = Field(
        default_factory=list, description="Recommended operational checks"
    )
    limitations: list[str] = Field(
        default_factory=list, description="System limitations and disclaimers"
    )


class AIAnalysisContextDTO(BaseModel):
    alert_id: uuid.UUID
    alert_type: str
    severity: str
    device_id: uuid.UUID | None = None
    elderly_id: uuid.UUID | None = None
    triggering_measurement: dict[str, Any] | None = None
    sensor_health: dict[str, Any] | None = None
    recent_measurements: list[dict[str, Any]] = Field(default_factory=list)


class AIAnalysisCreate(AIAnalysisBase):
    alert_id: uuid.UUID
    completed_at: datetime | None = None
    raw_response: dict[str, Any] | None = None

    @field_validator("completed_at")
    @classmethod
    def validate_completed_at(cls, v: datetime | None) -> datetime | None:
        if v is not None:
            return ensure_utc_datetime(v)
        return v


class AIAnalysisResponse(AIAnalysisBase):
    """Public API response for AI enrichment.

    Excludes raw_response to prevent leaking model metadata, tokens, or internal payload details.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: uuid.UUID
    created_at: datetime
    completed_at: datetime | None = None


class AIAnalysisAdminResponse(AIAnalysisResponse):
    """Privileged admin response that includes sanitized raw_response."""

    raw_response: dict[str, Any] | None = None
