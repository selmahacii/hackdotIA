"""AI Analysis and Enrichment Service."""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.integrations.nvidia_client import (
    AIClientError,
    AIClientParseError,
    AIClientTimeoutError,
    BaseAIClient,
    NVIDIAClient,
)
from app.models.ai_analysis import AIAnalysis
from app.models.enums import AIAnalysisStatus, AIProvider
from app.repositories.ai_analysis import AIAnalysisRepository
from app.repositories.alert import AlertRepository
from app.repositories.measurement import MeasurementRepository
from app.repositories.sensor_health import SensorHealthRepository
from app.services.ai_context import AIContextBuilder
from app.websocket.manager import ws_manager

logger = logging.getLogger(__name__)


class AIAnalysisService:
    """Orchestrates AI analysis and enrichment for alerts.

    Guarantees:
    - Asynchronous, non-blocking enrichment (alerts are created deterministically first).
    - Idempotency: avoids duplicate analysis unless forced.
    - Graceful fallback: on AI timeout, network, or parse errors, records a safe deterministic fallback.
    - Zero data leakage: strict data minimization via AIContextBuilder.
    """

    def __init__(
        self,
        session: AsyncSession,
        ai_client: BaseAIClient | None = None,
        context_builder: AIContextBuilder | None = None,
    ) -> None:
        self.session = session
        self.ai_analysis_repo = AIAnalysisRepository(session)
        self.alert_repo = AlertRepository(session)
        self.measurement_repo = MeasurementRepository(session)
        self.sensor_health_repo = SensorHealthRepository(session)
        self.context_builder = context_builder or AIContextBuilder()

        self.ai_client: BaseAIClient | None
        if ai_client is not None:
            self.ai_client = ai_client
        elif settings.NVIDIA_ENABLED:
            self.ai_client = NVIDIAClient()
        else:
            self.ai_client = None

    async def trigger_analysis(
        self,
        alert_id: uuid.UUID,
        force: bool = False,
    ) -> AIAnalysis:
        """Create or return an existing AIAnalysis record in PENDING state.

        Performs idempotency check: if an analysis is already RUNNING or COMPLETED, returns it.
        """
        alert = await self.alert_repo.get_by_id(alert_id)
        if not alert:
            raise ValueError(f"Alert with ID {alert_id} not found")

        if not force:
            existing = await self.ai_analysis_repo.get_active_or_completed_for_alert(alert_id)
            if existing:
                logger.info(
                    "AI analysis already exists for alert %s (status=%s, id=%s)",
                    alert_id,
                    existing.status.value,
                    existing.id,
                )
                return existing

        initial_provider = (
            AIProvider.NVIDIA if settings.NVIDIA_ENABLED else AIProvider.FALLBACK_RULES
        )
        model_name = settings.NVIDIA_MODEL if settings.NVIDIA_ENABLED else "deterministic_fallback"

        analysis = AIAnalysis(
            alert_id=alert_id,
            provider=initial_provider,
            status=AIAnalysisStatus.PENDING,
            model_name=model_name,
            created_at=datetime.now(UTC),
        )
        await self.ai_analysis_repo.create(analysis)
        logger.info("Triggered AI analysis %s for alert %s in PENDING state", analysis.id, alert_id)
        return analysis

    async def process_analysis(self, analysis_id: uuid.UUID) -> AIAnalysis:
        """Execute the enrichment workflow for a given analysis record."""
        analysis = await self.ai_analysis_repo.get_by_id(analysis_id)
        if not analysis:
            raise ValueError(f"AIAnalysis with ID {analysis_id} not found")

        alert = await self.alert_repo.get_by_id(analysis.alert_id)
        if not alert:
            analysis.status = AIAnalysisStatus.FAILED
            analysis.error = f"Alert {analysis.alert_id} not found during processing"
            await self.session.commit()
            return analysis

        # Transition to RUNNING
        analysis.status = AIAnalysisStatus.RUNNING
        await self.session.commit()
        await self.session.refresh(analysis)

        # Retrieve context
        measurement = None
        sensor_health = None
        measurement_id = None
        if alert.context and isinstance(alert.context, dict) and "measurement_id" in alert.context:
            try:
                measurement_id = uuid.UUID(str(alert.context["measurement_id"]))
            except (ValueError, TypeError):
                pass

        if measurement_id:
            measurement = await self.measurement_repo.get_by_id(measurement_id)
            sensor_health = await self.sensor_health_repo.get_by_measurement_id(measurement_id)
        elif alert.device_id:
            recent_seq = await self.measurement_repo.list_recent_by_device(alert.device_id, limit=1)
            if recent_seq:
                measurement = recent_seq[0]
                sensor_health = await self.sensor_health_repo.get_by_measurement_id(measurement.id)

        recent_measurements = []
        if alert.device_id:
            recent_seq = await self.measurement_repo.list_recent_by_device(alert.device_id, limit=5)
            recent_measurements = list(recent_seq)

        context_dto = self.context_builder.build_context_dto(
            alert=alert,
            measurement=measurement,
            sensor_health=sensor_health,
            recent_measurements=recent_measurements,
        )

        # Check if NVIDIA is enabled and client available
        if not settings.NVIDIA_ENABLED or self.ai_client is None:
            logger.info(
                "NVIDIA AI is disabled; generating deterministic fallback for alert %s", alert.id
            )
            fallback = self.context_builder.create_fallback_enrichment(
                alert_type=context_dto.alert_type,
                severity=context_dto.severity,
                reason="NVIDIA AI disabled by configuration",
            )
            analysis.provider = AIProvider.FALLBACK_RULES
            analysis.status = AIAnalysisStatus.FALLBACK
            analysis.risk_level = (
                alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)
            )
            analysis.anomaly_detected = True
            analysis.possible_event = fallback.summary[:100]
            analysis.explanation = fallback.summary[:500]
            analysis.recommended_action = "; ".join(fallback.recommended_checks)[:500]
            analysis.confidence = fallback.confidence
            analysis.completed_at = datetime.now(UTC)
            analysis.raw_response = fallback.model_dump()
            await self.session.commit()
            await self.session.refresh(analysis)

            await self._broadcast_completed(analysis)
            return analysis

        # Execute AI call
        try:
            system_prompt, user_prompt = self.context_builder.build_prompts(context_dto)
            response = await self.ai_client.analyze(system_prompt, user_prompt)

            analysis.provider = AIProvider.NVIDIA
            analysis.status = AIAnalysisStatus.COMPLETED
            analysis.risk_level = (
                alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)
            )
            analysis.anomaly_detected = True
            analysis.possible_event = response.result.summary[:100]
            analysis.explanation = response.result.summary[:500]
            analysis.recommended_action = "; ".join(response.result.recommended_checks)[:500]
            analysis.confidence = response.result.confidence
            analysis.model_name = response.model_name
            analysis.latency_ms = response.latency_ms
            analysis.completed_at = datetime.now(UTC)
            analysis.raw_response = response.raw_response
            analysis.error = None

            await self.session.commit()
            await self.session.refresh(analysis)
            logger.info(
                "AI analysis %s completed successfully in %d ms", analysis.id, response.latency_ms
            )

        except (AIClientTimeoutError, AIClientParseError, AIClientError, Exception) as exc:
            logger.warning(
                "AI analysis %s failed with %s: %s. Applying fallback.",
                analysis.id,
                type(exc).__name__,
                exc,
            )
            fallback = self.context_builder.create_fallback_enrichment(
                alert_type=context_dto.alert_type,
                severity=context_dto.severity,
                reason=f"{type(exc).__name__}: {exc}",
            )
            analysis.provider = AIProvider.FALLBACK_RULES
            analysis.status = AIAnalysisStatus.FALLBACK
            analysis.risk_level = (
                alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)
            )
            analysis.anomaly_detected = True
            analysis.possible_event = fallback.summary[:100]
            analysis.explanation = fallback.summary[:500]
            analysis.recommended_action = "; ".join(fallback.recommended_checks)[:500]
            analysis.confidence = fallback.confidence
            analysis.completed_at = datetime.now(UTC)
            analysis.raw_response = fallback.model_dump()
            analysis.error = f"{type(exc).__name__}: {exc}"

            await self.session.commit()
            await self.session.refresh(analysis)

        await self._broadcast_completed(analysis)
        return analysis

    async def run_enrichment_for_alert(
        self, alert_id: uuid.UUID, force: bool = False
    ) -> AIAnalysis:
        """Convenience method triggering and immediately processing analysis in sequence."""
        analysis = await self.trigger_analysis(alert_id, force=force)
        if (
            analysis.status
            in (
                AIAnalysisStatus.COMPLETED,
                AIAnalysisStatus.FALLBACK,
                AIAnalysisStatus.RUNNING,
            )
            and not force
        ):
            return analysis
        return await self.process_analysis(analysis.id)

    async def _broadcast_completed(self, analysis: AIAnalysis) -> None:
        try:
            await ws_manager.broadcast_ai_analysis_completed(
                alert_id=analysis.alert_id,
                analysis_id=analysis.id,
                status=analysis.status.value,
                risk_level=analysis.risk_level,
                confidence=analysis.confidence,
                summary=analysis.explanation,
                recommended_action=analysis.recommended_action,
            )
        except Exception as exc:
            logger.warning("Failed to broadcast WebSocket ai.analysis.completed: %s", exc)


async def run_enrichment_background(
    alert_id: uuid.UUID,
    ai_client: BaseAIClient | None = None,
    force: bool = False,
) -> None:
    """Standalone background task handler that creates its own isolated database session."""
    try:
        async with AsyncSessionLocal() as session:
            service = AIAnalysisService(session, ai_client=ai_client)
            await service.run_enrichment_for_alert(alert_id, force=force)
    except Exception as exc:
        logger.error(
            "Background AI enrichment task failed for alert %s: %s", alert_id, exc, exc_info=True
        )
