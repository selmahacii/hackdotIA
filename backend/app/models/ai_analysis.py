import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AIAnalysisStatus, AIProvider

if TYPE_CHECKING:
    from app.models.alert import Alert


class AIAnalysis(Base):
    __tablename__ = "ai_analysis"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider: Mapped[AIProvider] = mapped_column(
        SQLEnum(AIProvider, name="ai_provider_enum", native_enum=True),
        default=AIProvider.NVIDIA,
        nullable=False,
    )
    status: Mapped[AIAnalysisStatus] = mapped_column(
        SQLEnum(AIAnalysisStatus, name="ai_analysis_status_enum", native_enum=True),
        default=AIAnalysisStatus.PENDING,
        nullable=False,
    )

    risk_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    anomaly_detected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    possible_event: Mapped[str | None] = mapped_column(String(100), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    alert: Mapped["Alert"] = relationship(
        "Alert",
        back_populates="ai_analyses",
    )
