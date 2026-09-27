import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.elderly import ElderlyPerson
    from app.models.sensor_health import SensorHealth


class Measurement(Base):
    __tablename__ = "measurement"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        index=True,
        nullable=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("device.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    elderly_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("elderly_person.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # MAX30102 sensors (can be NULL if finger_detected is False)
    bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    spo2: Mapped[float | None] = mapped_column(Float, nullable=True)
    finger_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # DHT11 environmental sensor
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    # MPU6050 accelerometer & computed magnitude
    accel_x_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    accel_y_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    accel_z_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    accel_magnitude_g: Mapped[float | None] = mapped_column(Float, nullable=True)

    # GPS positioning (can be NULL if gps_fix_valid is False)
    gps_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_fix_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Device telemetry
    battery_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    wifi_rssi: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index("ix_measurement_device_measured_at", "device_id", "measured_at"),
        Index("ix_measurement_elderly_measured_at", "elderly_id", "measured_at"),
    )

    # Relationships
    device: Mapped["Device"] = relationship(
        "Device",
        back_populates="measurements",
    )
    elderly: Mapped["ElderlyPerson"] = relationship(
        "ElderlyPerson",
        back_populates="measurements",
    )
    sensor_health: Mapped[Optional["SensorHealth"]] = relationship(
        "SensorHealth",
        back_populates="measurement",
        uselist=False,
        cascade="all, delete-orphan",
    )
