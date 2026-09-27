import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AlertSeverity, AlertSource, AlertStatus, AlertType

if TYPE_CHECKING:
    from app.models.ai_analysis import AIAnalysis
    from app.models.device import Device
    from app.models.elderly import ElderlyPerson


class Alert(Base):
    __tablename__ = "alert"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    elderly_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("elderly_person.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("device.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    alert_type: Mapped[AlertType] = mapped_column(
        SQLEnum(AlertType, name="alert_type_enum", native_enum=True),
        nullable=False,
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        SQLEnum(AlertSeverity, name="alert_severity_enum", native_enum=True),
        nullable=False,
    )
    status: Mapped[AlertStatus] = mapped_column(
        SQLEnum(AlertStatus, name="alert_status_enum", native_enum=True),
        default=AlertStatus.OPEN,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    source: Mapped[AlertSource] = mapped_column(
        SQLEnum(AlertSource, name="alert_source_enum", native_enum=True),
        default=AlertSource.RULE_ENGINE,
        nullable=False,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Indexes & Partial Unique Index
    __table_args__ = (
        Index("ix_alert_elderly_created_at", "elderly_id", "created_at"),
        Index("ix_alert_elderly_status", "elderly_id", "status"),
        Index("ix_alert_type_status", "alert_type", "status"),
        Index("ix_alert_dedup_status", "dedup_key", "status"),
        # Partial unique index: only 1 active alert (OPEN or ACKNOWLEDGED) allowed per dedup_key
        Index(
            "uq_alert_active_dedup_key",
            "dedup_key",
            unique=True,
            postgresql_where=text("status IN ('OPEN', 'ACKNOWLEDGED')"),
        ),
    )

    # Relationships
    elderly: Mapped["ElderlyPerson"] = relationship(
        "ElderlyPerson",
        back_populates="alerts",
    )
    device: Mapped[Optional["Device"]] = relationship(
        "Device",
        back_populates="alerts",
    )
    ai_analyses: Mapped[list["AIAnalysis"]] = relationship(
        "AIAnalysis",
        back_populates="alert",
        cascade="all, delete-orphan",
    )
