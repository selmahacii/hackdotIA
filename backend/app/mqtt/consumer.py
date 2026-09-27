import asyncio
import json
import time
from datetime import UTC, datetime
from typing import Any

import aiomqtt

from app.config import settings
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.mqtt.client import mqtt_metrics
from app.mqtt.errors import (
    DuplicateEventError,
    InvalidPayloadError,
    TopicMismatchError,
    UnknownDeviceError,
)
from app.mqtt.service import MQTTIngestionService
from app.mqtt.topics import get_topic_filter, parse_topic
from app.services.processing import ProcessingService


class MQTTConsumer:
    """Robust, resilient background MQTT consumer with exponential backoff and structured logging."""

    def __init__(self) -> None:
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the background consumer task."""
        if self._task and not self._task.done():
            logger.warning("MQTT consumer task is already running")
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self.run(), name="mqtt_consumer")
        logger.info("MQTT consumer background task initiated")

    async def stop(self) -> None:
        """Gracefully stop the background consumer task."""
        logger.info("Stopping MQTT consumer...")
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        mqtt_metrics.mark_disconnected()
        logger.info("MQTT consumer stopped successfully")

    async def run(self) -> None:
        reconnect_delay = settings.MQTT_RECONNECT_DELAY

        while not self._stop_event.is_set():
            mqtt_metrics.mark_connecting()
            logger.info(
                f"Attempting connection to MQTT broker at {settings.MQTT_HOST}:{settings.MQTT_PORT} "
                f"(clean_session={settings.MQTT_CLEAN_SESSION}, qos={settings.MQTT_QOS})..."
            )

            try:
                async with aiomqtt.Client(
                    hostname=settings.MQTT_HOST,
                    port=settings.MQTT_PORT,
                    username=settings.MQTT_USER or None,
                    password=settings.MQTT_PASSWORD or None,
                    keepalive=settings.MQTT_KEEPALIVE,
                    clean_session=settings.MQTT_CLEAN_SESSION,
                ) as client:
                    mqtt_metrics.mark_connected()
                    reconnect_delay = settings.MQTT_RECONNECT_DELAY
                    logger.info("mqtt_connected: successfully connected to broker")

                    # Subscribe to topics
                    for topic_filter in get_topic_filter():
                        await client.subscribe(topic_filter, qos=settings.MQTT_QOS)
                        logger.info(
                            f"subscription_success: subscribed to '{topic_filter}' (QoS {settings.MQTT_QOS})"
                        )

                    async for message in client.messages:
                        if self._stop_event.is_set():
                            break
                        await self.process_message(message)

            except asyncio.CancelledError:
                logger.info("MQTT consumer loop cancelled")
                break
            except aiomqtt.MqttError as err:
                mqtt_metrics.mark_disconnected()
                logger.warning(
                    f"MQTT connection lost or failed: {err}. Reconnecting in {reconnect_delay:.1f}s..."
                )
                mqtt_metrics.mark_reconnecting()
                try:
                    await asyncio.sleep(reconnect_delay)
                except asyncio.CancelledError:
                    break
                reconnect_delay = min(reconnect_delay * 2, settings.MQTT_MAX_RECONNECT_DELAY)
            except Exception as err:
                mqtt_metrics.mark_disconnected()
                logger.error(
                    f"Unexpected error in MQTT consumer: {err}. Retrying in {reconnect_delay:.1f}s..."
                )
                try:
                    await asyncio.sleep(reconnect_delay)
                except asyncio.CancelledError:
                    break
                reconnect_delay = min(reconnect_delay * 2, settings.MQTT_MAX_RECONNECT_DELAY)

    async def process_message(self, message: aiomqtt.Message) -> None:
        start_time = time.monotonic()
        now_utc = datetime.now(UTC)
        raw_topic = str(message.topic)
        mqtt_metrics.messages_received += 1

        # 1. Parse topic
        parsed = parse_topic(raw_topic)
        if not parsed:
            logger.warning(
                f"mqtt_message_rejected: unhandled or invalid topic structure: '{raw_topic}'"
            )
            return

        topic_device_uid, message_type = parsed

        # 2. Decode UTF-8 and parse JSON
        try:
            payload_str = (
                message.payload.decode("utf-8")
                if isinstance(message.payload, bytes)
                else str(message.payload)
            )
            payload_dict: dict[str, Any] = json.loads(payload_str)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            mqtt_metrics.validation_errors += 1
            logger.warning(
                f"mqtt_validation_failed: invalid JSON or non-UTF8 payload on topic '{raw_topic}': {e}"
            )
            return

        # 3. Process with transactional boundary
        async with AsyncSessionLocal() as session:
            service = MQTTIngestionService(session)
            try:
                if message_type == "telemetry":
                    measurement = await service.ingest_telemetry(
                        payload_data=payload_dict,
                        topic_device_uid=topic_device_uid,
                    )
                    duration_ms = (time.monotonic() - start_time) * 1000
                    clock_delta_s = (now_utc - measurement.measured_at).total_seconds()
                    mqtt_metrics.messages_processed += 1
                    logger.info(
                        f"measurement_persisted: device_uid='{topic_device_uid}', "
                        f"event_id='{measurement.event_id}', elderly_id='{measurement.elderly_id}', "
                        f"latency_ms={duration_ms:.2f}, clock_delta_s={clock_delta_s:.2f}"
                    )

                    # 4. Post-ingestion deterministic processing (Sensor Health)
                    try:
                        processing_service = ProcessingService(session)
                        await processing_service.process_measurement(measurement)
                    except Exception as pe:
                        logger.error(
                            f"processing_failed: unexpected processing error on measurement '{measurement.id}': {pe}",
                            exc_info=True,
                        )

                elif message_type == "status":
                    device = await service.ingest_status(
                        payload_data=payload_dict,
                        topic_device_uid=topic_device_uid,
                    )
                    duration_ms = (time.monotonic() - start_time) * 1000
                    mqtt_metrics.messages_processed += 1
                    logger.info(
                        f"device_status_updated: device_uid='{device.device_uid}', "
                        f"status='{device.status.value}', latency_ms={duration_ms:.2f}"
                    )

                elif message_type == "health":
                    health = await service.ingest_health(
                        payload_data=payload_dict,
                        topic_device_uid=topic_device_uid,
                    )
                    duration_ms = (time.monotonic() - start_time) * 1000
                    mqtt_metrics.messages_processed += 1
                    logger.info(
                        f"sensor_health_persisted: device_uid='{topic_device_uid}', "
                        f"health_id='{health.id}', latency_ms={duration_ms:.2f}"
                    )

            except DuplicateEventError as e:
                mqtt_metrics.duplicates_detected += 1
                logger.info(
                    f"mqtt_duplicate_event: event_id='{e.event_id}' already processed, ignoring cleanly"
                )
            except UnknownDeviceError as e:
                mqtt_metrics.unknown_devices += 1
                logger.warning(
                    f"mqtt_unknown_device: unregistered device_uid='{e.device_uid}' on topic '{raw_topic}', message rejected"
                )
            except TopicMismatchError as e:
                mqtt_metrics.topic_mismatches += 1
                logger.warning(
                    f"mqtt_topic_mismatch: topic uid '{e.topic_uid}' != payload uid '{e.payload_uid}', message rejected"
                )
            except InvalidPayloadError as e:
                mqtt_metrics.validation_errors += 1
                logger.warning(
                    f"mqtt_validation_failed: payload schema violation on topic '{raw_topic}': {e.reason}"
                )
            except Exception as e:
                logger.error(
                    f"mqtt_processing_error: unexpected error handling message on '{raw_topic}': {e}",
                    exc_info=True,
                )


# Global consumer instance
mqtt_consumer = MQTTConsumer()
