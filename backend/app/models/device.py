import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DeviceStatus

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.elderly import ElderlyPerson
    from app.models.measurement import Measurement


class Device(Base):
    __tablename__ = "device"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    device_uid: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    elderly_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("elderly_person.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[DeviceStatus] = mapped_column(
        SQLEnum(DeviceStatus, name="device_status_enum", native_enum=True),
        default=DeviceStatus.UNKNOWN,
        nullable=False,
    )
    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    battery_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    wifi_rssi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capabilities: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

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

    # Indexes
    __table_args__ = (Index("ix_device_elderly_status", "elderly_id", "status"),)

    # Relationships
    elderly: Mapped["ElderlyPerson"] = relationship(
        "ElderlyPerson",
        back_populates="devices",
    )
    measurements: Mapped[list["Measurement"]] = relationship(
        "Measurement",
        back_populates="device",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert",
        back_populates="device",
    )
