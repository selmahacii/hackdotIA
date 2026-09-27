import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import SensorHealthStatus

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.measurement import Measurement


class SensorHealth(Base):
    __tablename__ = "sensor_health"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    measurement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("measurement.id", ondelete="CASCADE"),
        unique=True,
        nullable=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("device.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    max30102_status: Mapped[SensorHealthStatus] = mapped_column(
        SQLEnum(SensorHealthStatus, name="sensor_health_status_enum", native_enum=True),
        default=SensorHealthStatus.UNKNOWN,
        nullable=False,
    )
    dht11_status: Mapped[SensorHealthStatus] = mapped_column(
        SQLEnum(SensorHealthStatus, name="sensor_health_status_enum", native_enum=True),
        default=SensorHealthStatus.UNKNOWN,
        nullable=False,
    )
    mpu6050_status: Mapped[SensorHealthStatus] = mapped_column(
        SQLEnum(SensorHealthStatus, name="sensor_health_status_enum", native_enum=True),
        default=SensorHealthStatus.UNKNOWN,
        nullable=False,
    )
    gps_status: Mapped[SensorHealthStatus] = mapped_column(
        SQLEnum(SensorHealthStatus, name="sensor_health_status_enum", native_enum=True),
        default=SensorHealthStatus.UNKNOWN,
        nullable=False,
    )

    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    measurement: Mapped["Measurement"] = relationship(
        "Measurement",
        back_populates="sensor_health",
    )
    device: Mapped["Device"] = relationship("Device")
