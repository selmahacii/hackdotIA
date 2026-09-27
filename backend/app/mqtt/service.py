from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.enums import DeviceStatus
from app.models.measurement import Measurement
from app.models.sensor_health import SensorHealth
from app.mqtt.errors import (
    DuplicateEventError,
    InvalidPayloadError,
    TopicMismatchError,
    UnknownDeviceError,
)
from app.repositories.device import DeviceRepository
from app.repositories.measurement import MeasurementRepository
from app.schemas.telemetry import (
    DeviceStatusPayload,
    SensorHealthPayload,
    SensorTelemetryPayload,
)


class MQTTIngestionService:
    """Core domain service for validating and persisting MQTT payloads."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.device_repo = DeviceRepository(session)
        self.measurement_repo = MeasurementRepository(session)

    async def ingest_telemetry(
        self,
        payload_data: dict[str, Any],
        topic_device_uid: str,
    ) -> Measurement:
        """
        Validates telemetry payload, verifies device registration,
        enforces idempotency via event_id, and atomically persists
        the Measurement while updating Device last_seen and status.
        """
        try:
            payload = SensorTelemetryPayload.model_validate(payload_data)
        except ValidationError as e:
            raise InvalidPayloadError(
                reason="SensorTelemetryPayload validation failed",
                details=e.errors(),
            ) from e

        if payload.device_uid != topic_device_uid:
            raise TopicMismatchError(
                topic_uid=topic_device_uid,
                payload_uid=payload.device_uid,
            )

        device = await self.device_repo.get_by_uid(payload.device_uid)
        if not device:
            raise UnknownDeviceError(device_uid=payload.device_uid)

        # Application-level idempotency pre-check
        existing_measurement = await self.measurement_repo.get_by_event_id(payload.event_id)
        if existing_measurement:
            raise DuplicateEventError(event_id=str(payload.event_id))

        now_utc = datetime.now(UTC)
        measurement = Measurement(
            event_id=payload.event_id,
            device_id=device.id,
            elderly_id=device.elderly_id,
            received_at=now_utc,
            measured_at=payload.timestamp,
            bpm=payload.bpm,
            spo2=payload.spo2,
            finger_detected=payload.finger_detected,
            temperature_c=payload.temperature_c,
            humidity_percent=payload.humidity_percent,
            accel_x_g=payload.accel_x_g,
            accel_y_g=payload.accel_y_g,
            accel_z_g=payload.accel_z_g,
            accel_magnitude_g=payload.accel_magnitude_g,
            gps_latitude=payload.gps_latitude,
            gps_longitude=payload.gps_longitude,
            gps_fix_valid=payload.gps_fix_valid,
            battery_level=(
                float(payload.battery_level) if payload.battery_level is not None else None
            ),
            wifi_rssi=payload.wifi_rssi,
        )

        # Update Device state
        device.last_seen_at = now_utc
        device.status = DeviceStatus.ONLINE
        if payload.battery_level is not None:
            device.battery_level = float(payload.battery_level)
        if payload.wifi_rssi is not None:
            device.wifi_rssi = payload.wifi_rssi

        self.session.add(measurement)

        try:
            await self.session.commit()
            await self.session.refresh(measurement)
            return measurement
        except IntegrityError as e:
            await self.session.rollback()
            # If concurrent duplicate event inserted
            if "event_id" in str(e) or "ix_measurement_event_id" in str(e):
                raise DuplicateEventError(event_id=str(payload.event_id)) from e
            raise

    async def ingest_status(
        self,
        payload_data: dict[str, Any],
        topic_device_uid: str,
    ) -> Device:
        """
        Validates status payload and updates device lifecycle/connectivity state.
        Does NOT insert a Measurement.
        """
        try:
            payload = DeviceStatusPayload.model_validate(payload_data)
        except ValidationError as e:
            raise InvalidPayloadError(
                reason="DeviceStatusPayload validation failed",
                details=e.errors(),
            ) from e

        if payload.device_uid != topic_device_uid:
            raise TopicMismatchError(
                topic_uid=topic_device_uid,
                payload_uid=payload.device_uid,
            )

        device = await self.device_repo.get_by_uid(payload.device_uid)
        if not device:
            raise UnknownDeviceError(device_uid=payload.device_uid)

        device.status = payload.status
        device.last_seen_at = payload.timestamp
        if payload.battery_level is not None:
            device.battery_level = float(payload.battery_level)
        if payload.wifi_rssi is not None:
            device.wifi_rssi = payload.wifi_rssi
        if payload.firmware_version is not None:
            device.firmware_version = payload.firmware_version

        await self.session.commit()
        await self.session.refresh(device)
        return device

    async def ingest_health(
        self,
        payload_data: dict[str, Any],
        topic_device_uid: str,
    ) -> SensorHealth:
        """
        Validates sensor health diagnostic report and persists it independently.
        """
        try:
            payload = SensorHealthPayload.model_validate(payload_data)
        except ValidationError as e:
            raise InvalidPayloadError(
                reason="SensorHealthPayload validation failed",
                details=e.errors(),
            ) from e

        if payload.device_uid != topic_device_uid:
            raise TopicMismatchError(
                topic_uid=topic_device_uid,
                payload_uid=payload.device_uid,
            )

        device = await self.device_repo.get_by_uid(payload.device_uid)
        if not device:
            raise UnknownDeviceError(device_uid=payload.device_uid)

        health = SensorHealth(
            device_id=device.id,
            measurement_id=None,
            max30102_status=payload.max30102_status,
            dht11_status=payload.dht11_status,
            mpu6050_status=payload.mpu6050_status,
            gps_status=payload.gps_status,
            details=payload.details,
            checked_at=payload.timestamp,
        )

        now_utc = datetime.now(UTC)
        device.last_seen_at = now_utc

        self.session.add(health)
        await self.session.commit()
        await self.session.refresh(health)
        return health
