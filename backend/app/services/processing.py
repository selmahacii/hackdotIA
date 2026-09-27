import time
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.measurement import Measurement
from app.models.sensor_health import SensorHealth
from app.repositories.device import DeviceRepository
from app.repositories.measurement import MeasurementRepository
from app.repositories.sensor_health import SensorHealthRepository
from app.services.sensor_health import SensorHealthService


class ProcessingService:
    """
    Orchestrates post-ingestion deterministic processing pipelines.
    Evaluates sensor health and prepares structured signals for future rule engines.
    Guarantees idempotency and ensures failures in processing do NOT compromise
    raw telemetry measurements.
    """

    def __init__(
        self,
        session: AsyncSession,
        sensor_health_service: SensorHealthService | None = None,
    ) -> None:
        self.session = session
        self.measurement_repo = MeasurementRepository(session)
        self.device_repo = DeviceRepository(session)
        self.sensor_health_repo = SensorHealthRepository(session)
        self.sensor_health_service = sensor_health_service or SensorHealthService()

    async def process_measurement(
        self,
        measurement: Measurement,
        now: datetime | None = None,
    ) -> SensorHealth | None:
        """
        Executes the processing pipeline for a persisted measurement.
        1. Checks idempotency (SensorHealth already evaluated for this measurement_id).
        2. Retrieves recent device history.
        3. Evaluates sensor health via SensorHealthService.
        4. Persists the SensorHealth entity atomically.
        """
        start_time = time.monotonic()
        measurement_id = measurement.id
        device_id = measurement.device_id

        # 1. Idempotency Check
        existing_health = await self.sensor_health_repo.get_by_measurement_id(measurement_id)
        if existing_health:
            logger.info(
                f"sensor_health_already_processed: measurement_id='{measurement_id}', "
                f"sensor_health_id='{existing_health.id}', returning existing record"
            )
            return existing_health

        try:
            # 2. Load context: device & recent measurement history
            device = await self.device_repo.get_by_id(device_id)
            history = await self.measurement_repo.list_recent_by_device(
                device_id=device_id,
                limit=100,
            )

            # 3. Evaluate Sensor Health
            evaluation = self.sensor_health_service.evaluate(
                measurement=measurement,
                history=history,
                device=device,
                now=now,
            )

            # 4. Construct SensorHealth entity
            sensor_health = SensorHealth(
                measurement_id=measurement.id,
                device_id=measurement.device_id,
                max30102_status=evaluation.max30102_status,
                dht11_status=evaluation.dht11_status,
                mpu6050_status=evaluation.mpu6050_status,
                gps_status=evaluation.gps_status,
                details=evaluation.details,
                checked_at=datetime.now(UTC),
            )

            self.session.add(sensor_health)
            await self.session.commit()
            await self.session.refresh(sensor_health)

            latency_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                f"sensor_health_evaluated: measurement_id='{measurement.id}', "
                f"device_id='{measurement.device_id}', health_id='{sensor_health.id}', "
                f"max30102='{sensor_health.max30102_status.value}', "
                f"dht11='{sensor_health.dht11_status.value}', "
                f"mpu6050='{sensor_health.mpu6050_status.value}', "
                f"gps='{sensor_health.gps_status.value}', latency_ms={latency_ms:.2f}"
            )

            return sensor_health

        except IntegrityError:
            await self.session.rollback()
            # In case of concurrent evaluation of the same measurement_id
            existing = await self.sensor_health_repo.get_by_measurement_id(measurement_id)
            if existing:
                logger.info(
                    f"sensor_health_concurrent_duplicate: measurement_id='{measurement_id}' "
                    f"already persisted by concurrent transaction"
                )
                return existing
            raise

        except Exception as e:
            await self.session.rollback()
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                f"processing_failed: failed evaluating sensor health for measurement_id='{measurement_id}', "
                f"device_id='{device_id}': {e}, latency_ms={latency_ms:.2f}",
                exc_info=True,
            )
            # Crucial: return None and do NOT re-raise to protect the already persisted Measurement
            return None
