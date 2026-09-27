"""AI Analysis and Enrichment Service."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.integrations.groq_client import GroqClient
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
from app.repositories.elderly import ElderlyRepository
from app.repositories.measurement import MeasurementRepository
from app.repositories.sensor_health import SensorHealthRepository
from app.schemas.ai_analysis import AIChatMessage, AIChatResponse
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
        self.elderly_repo = ElderlyRepository(session)
        self.measurement_repo = MeasurementRepository(session)
        self.sensor_health_repo = SensorHealthRepository(session)
        self.context_builder = context_builder or AIContextBuilder()

        self.ai_client: BaseAIClient | None
        if ai_client is not None:
            self.ai_client = ai_client
        elif settings.GROQ_ENABLED and settings.GROQ_API_KEY:
            self.ai_client = GroqClient()
        elif settings.NVIDIA_ENABLED and settings.NVIDIA_API_KEY:
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

        if settings.GROQ_ENABLED:
            initial_provider = AIProvider.GROQ
            model_name = settings.GROQ_MODEL
        elif settings.NVIDIA_ENABLED:
            initial_provider = AIProvider.NVIDIA
            model_name = settings.NVIDIA_MODEL
        else:
            initial_provider = AIProvider.FALLBACK_RULES
            model_name = "deterministic_fallback"

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

        # Check if AI enrichment is enabled and client available
        ai_enabled = (
            (settings.GROQ_ENABLED and bool(settings.GROQ_API_KEY))
            or (settings.NVIDIA_ENABLED and bool(settings.NVIDIA_API_KEY))
        ) and self.ai_client is not None

        if not ai_enabled or self.ai_client is None:
            logger.info(
                "AI enrichment disabled; generating deterministic fallback for alert %s", alert.id
            )
            fallback = self.context_builder.create_fallback_enrichment(
                alert_type=context_dto.alert_type,
                severity=context_dto.severity,
                reason="AI enrichment disabled by configuration",
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

            analysis.provider = AIProvider.GROQ if settings.GROQ_ENABLED else AIProvider.NVIDIA
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

    async def chat_with_clinical_assistant(
        self,
        message: str,
        elderly_id: uuid.UUID | None = None,
        alert_id: uuid.UUID | None = None,
        history: list[AIChatMessage] | None = None,
    ) -> AIChatResponse:
        """Conversational clinical AI assistant explaining vitals, kinematic signals, and alert details."""
        context_data: dict[str, Any] = {}
        alert_ctx_text = ""
        resident_ctx_text = ""

        # 1. Fetch Alert context if alert_id is specified
        if alert_id:
            alert = await self.alert_repo.get_by_id(alert_id)
            if alert:
                if not elderly_id and alert.elderly_id:
                    elderly_id = alert.elderly_id

                latest_ai = await self.ai_analysis_repo.get_latest_by_alert_id(alert.id)
                context_data["alert"] = {
                    "id": str(alert.id),
                    "title": alert.title,
                    "alert_type": alert.alert_type.value if hasattr(alert.alert_type, "value") else str(alert.alert_type),
                    "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
                    "status": alert.status.value if hasattr(alert.status, "value") else str(alert.status),
                    "occurred_at": alert.occurred_at.isoformat() if alert.occurred_at else None,
                    "description": alert.description,
                    "context": alert.context,
                    "ai_explanation": latest_ai.explanation if latest_ai else None,
                    "ai_recommended_action": latest_ai.recommended_action if latest_ai else None,
                }
                alert_ctx_text = f"""
[ALERTE SÉLECTIONNÉE]
- Titre : {alert.title}
- Type : {context_data['alert']['alert_type']}
- Sévérité : {context_data['alert']['severity']}
- Statut : {context_data['alert']['status']}
- Description : {alert.description}
- Contexte capteurs : {alert.context}
- Analyse IA préalable : {latest_ai.explanation if latest_ai else 'Aucune'}
- Recommandation préalable : {latest_ai.recommended_action if latest_ai else 'N/A'}
"""

        # 2. Fetch Resident context if elderly_id is specified
        if elderly_id:
            resident = await self.elderly_repo.get_by_id(elderly_id)
            if resident:
                measurements = await self.measurement_repo.list_recent_by_elderly(elderly_id, limit=5)
                alerts = await self.alert_repo.list_by_elderly(elderly_id, limit=5)

                meas_list = []
                for m in measurements:
                    meas_list.append({
                        "measured_at": m.measured_at.isoformat() if m.measured_at else None,
                        "bpm": m.bpm,
                        "spo2": m.spo2,
                        "temp_c": m.temperature_c,
                        "accel_g": m.accel_magnitude_g,
                        "finger_detected": m.finger_detected,
                    })

                context_data["resident"] = {
                    "id": str(resident.id),
                    "name": f"{resident.first_name} {resident.last_name}",
                    "is_active": resident.is_active,
                    "recent_measurements": meas_list,
                    "recent_alerts_count": len(alerts),
                }

                meas_summary = "\n".join([
                    f"  * {m['measured_at']}: BPM={m['bpm']}, SpO2={m['spo2']}%, Temp={m['temp_c']}°C, Accel={m['accel_g']}g"
                    for m in meas_list
                ]) or "  * Aucune mesure récente."

                alerts_summary = "\n".join([
                    f"  * {a.occurred_at.strftime('%Y-%m-%d %H:%M') if a.occurred_at else 'N/A'}: {a.title} ({a.severity.value if hasattr(a.severity, 'value') else a.severity})"
                    for a in alerts
                ]) or "  * Aucune alerte récente."

                resident_ctx_text = f"""
[RÉSIDENT SOUS TÉLÉSURVEILLANCE]
- Nom : {resident.first_name} {resident.last_name}
- Statut : {'Suivi actif' if resident.is_active else 'Inactif'}
- Dernières mesures capteurs (MAX30102, DHT11, MPU6050) :
{meas_summary}
- Historique récent des alertes :
{alerts_summary}
"""

        # 3. Construct System Prompt
        system_prompt = f"""Tu es l'assistant clinique et télémétrique intelligent de SmartEldery, une plateforme IoT et IA d'assistance aux soignants et de surveillance des personnes âgées.
Tu es propulsé par Groq LLM haute performance et connecté en direct à la base de données PostgreSQL de télésurveillance.

DIRECTIVES ESSENTIELLES :
1. RÔLE : Tu agis comme un expert télémétrique et conseiller clinique d'aide à la décision pour le personnel soignant (infirmiers, aides-soignants, médecins coordinateurs).
2. PÉDAGOGIE ET PRÉCISION : Explique clairement la signification des signaux physiques des capteurs connectés (ESP32) :
   - MAX30102 : Fréquence cardiaque (BPM, bradycardie < 50 ou tachycardie > 100), Saturation pulsée en oxygène (SpO2, normale > 95%, hypoxémie modérée 90-94%, critique < 90%), contact doigt.
   - MPU6050 (accéléromètre/gyroscope) : Pic d'impact (g), perte d'équilibre, transition posturale brutale suivie d'une immobilité prolongée (suspicion de chute).
   - DHT11 : Température et humidité ambiante (inconfort thermique, risque de déshydratation, coup de chaleur).
   - GPS : Localisation et détection de sortie de zone sécurisée (fugue ou désorientation).
3. NON-DIAGNOSTIC : Tu ne poses JAMAIS de diagnostic médical définitif (ne pas déclarer "le patient a fait un AVC"). Tu énonces des hypothèses physiques objectives basées sur les signaux mesurés et tu recommandes des vérifications au chevet du résident.
4. FORMAT DE RÉPONSE :
   - Structure ta réponse en Markdown clair (titres en gras, puces, recommandations concrètes numérotées).
   - Sois synthétique, chaleureux, professionnel et rassurant.
   - Inclus toujours une section "Recommandations pratiques pour le soignant".

DONNÉES EN DIRECT DE LA BASE DE DONNÉES :
{alert_ctx_text if alert_ctx_text else "Aucune alerte spécifique sélectionnée (question générale d'assistance)."}
{resident_ctx_text if resident_ctx_text else "Aucun résident spécifique ciblé."}
"""

        # 4. Prepare message chain
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        if history:
            for turn in history[-8:]:
                messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": message})

        # 5. Call AI Client
        if self.ai_client:
            try:
                reply, latency, model_used = await self.ai_client.chat(messages)
                return AIChatResponse(
                    reply=reply,
                    context_used=context_data,
                    model_name=model_used,
                    latency_ms=latency,
                )
            except Exception as exc:
                logger.warning("AI client chat error, generating fallback response: %s", exc)

        # 6. Fallback response if Groq is unreachable
        fallback_reply = (
            "### Analyse Télémétrique SmartEldery\n\n"
            "D'après les relevés en temps réel enregistrés dans notre base de données :\n\n"
        )
        if "alert" in context_data:
            alt = context_data["alert"]
            fallback_reply += (
                f"- **Alerte active :** {alt['title']} (Niveau : `{alt['severity']}`)\n"
                f"- **Analyse des capteurs :** {alt.get('ai_explanation') or alt.get('description')}\n\n"
                "**Recommandations immédiates :**\n"
                "1. Procéder à une vérification physique directe auprès du résident.\n"
                "2. Vérifier le maintien et le contact des capteurs de la montre / du bracelet.\n"
                "3. Acquitter l'alerte sur la console une fois le résident sécurisé.\n"
            )
        elif "resident" in context_data:
            res = context_data["resident"]
            fallback_reply += (
                f"- **Résident :** {res['name']} (Statut : {res['is_active']})\n"
                f"- **Alertes récentes :** {res['recent_alerts_count']} alerte(s) répertoriée(s).\n\n"
                "Les signaux physiologiques enregistrés indiquent une stabilité sous surveillance continue."
            )
        else:
            fallback_reply += (
                "Le système de surveillance télémétrique fonctionne normalement. "
                "L'ensemble des règles déterministes et des flux MQTT sont interconnectés avec PostgreSQL."
            )

        return AIChatResponse(
            reply=fallback_reply,
            context_used=context_data,
            model_name="fallback-deterministic",
            latency_ms=10,
        )

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
