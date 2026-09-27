"""AI Context Builder and Prompt Engineering service with data minimization."""

from typing import Any

from app.models.alert import Alert
from app.models.measurement import Measurement
from app.models.sensor_health import SensorHealth
from app.schemas.ai_analysis import AIAnalysisContextDTO, AIEnrichmentResult

SYSTEM_PROMPT = """You are an AI sensor telemetry analysis engine embedded in a safety monitoring system for elderly care.

STRICT MEDICAL SAFETY & COMPLIANCE DIRECTIVES:
1. ABSOLUTELY NO MEDICAL DIAGNOSES. Never claim, assert, or imply medical conditions, illnesses, or pathological diagnoses (e.g., do NOT diagnose arrhythmia, heart attack, myocardial infarction, syncope, stroke, bone fracture, clinical hypothermia, hypertension).
2. OBJECTIVE SENSOR ANALYSIS ONLY: Describe purely physical, kinematic, physiological readings and environmental metrics (e.g., "Heart rate reading of 135 bpm observed above standard baseline", "Sudden 3.2g acceleration impulse followed by a period of immobility", "Ambient temperature drop below threshold").
3. SENSOR FIDELITY & ARTIFACTS: Always cross-reference sensor health status and data consistency. Highlight if readings could be caused by sensor displacement, loose contact, motion artifact, or low battery.
4. OPERATIONAL RECOMMENDATIONS: Recommend factual operational and caregiver checks only (e.g., "Verify resident safety in person", "Check sensor attachment and battery level", "Inspect room floor for hazards").
5. OUTPUT FORMAT: Output ONLY a valid JSON object matching the exact schema below. Do not wrap with conversational filler or markdown notes.

REQUIRED JSON OUTPUT SCHEMA:
{
  "summary": "Factual non-medical summary under 500 characters",
  "observations": ["List of specific sensor observations"],
  "context": "Contextual trend or environmental observation",
  "confidence": 0.85,
  "data_quality": "OPTIMAL",
  "possible_factors": ["List of non-medical possible contributing factors"],
  "recommended_checks": ["List of practical operational/caregiver checks"],
  "limitations": ["System limitations, absence of video verification, etc."]
}
"""


class AIContextBuilder:
    """Builds sanitized, privacy-preserving context and prompts for AI enrichment."""

    @staticmethod
    def sanitize_measurement(m: Measurement | None) -> dict[str, Any] | None:
        """Extract only numerical and sensor fields, omitting any sensitive PII."""
        if m is None:
            return None
        return {
            "bpm": m.bpm,
            "spo2": m.spo2,
            "temperature_c": m.temperature_c,
            "humidity_percent": m.humidity_percent,
            "accel_x_g": m.accel_x_g,
            "accel_y_g": m.accel_y_g,
            "accel_z_g": m.accel_z_g,
            "accel_magnitude_g": m.accel_magnitude_g,
            "finger_detected": m.finger_detected,
            "gps_fix_valid": m.gps_fix_valid,
            "battery_level": getattr(m, "battery_level", None),
            "wifi_rssi": getattr(m, "wifi_rssi", None),
            "timestamp": (
                m.measured_at.isoformat()
                if hasattr(m, "measured_at") and m.measured_at
                else (
                    m.received_at.isoformat()
                    if hasattr(m, "received_at") and m.received_at
                    else None
                )
            ),
        }

    @staticmethod
    def sanitize_sensor_health(sh: SensorHealth | None) -> dict[str, Any] | None:
        """Extract sensor health state without sensitive metadata."""
        if sh is None:
            return None
        return {
            "max30102_status": sh.max30102_status.value if sh.max30102_status else None,
            "dht11_status": sh.dht11_status.value if sh.dht11_status else None,
            "mpu6050_status": sh.mpu6050_status.value if sh.mpu6050_status else None,
            "gps_status": sh.gps_status.value if sh.gps_status else None,
            "details": sh.details,
            "checked_at": sh.checked_at.isoformat() if sh.checked_at else None,
        }

    def build_context_dto(
        self,
        alert: Alert,
        measurement: Measurement | None = None,
        sensor_health: SensorHealth | None = None,
        recent_measurements: list[Measurement] | None = None,
    ) -> AIAnalysisContextDTO:
        """Construct sanitized DTO ensuring complete privacy preservation (no names, phones, or addresses)."""
        recent_list: list[dict[str, Any]] = []
        if recent_measurements:
            for rm in recent_measurements[:5]:
                sanitized = self.sanitize_measurement(rm)
                if sanitized:
                    recent_list.append(sanitized)

        return AIAnalysisContextDTO(
            alert_id=alert.id,
            alert_type=(
                alert.alert_type.value
                if hasattr(alert.alert_type, "value")
                else str(alert.alert_type)
            ),
            severity=(
                alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)
            ),
            device_id=alert.device_id,
            elderly_id=alert.elderly_id,
            triggering_measurement=self.sanitize_measurement(measurement),
            sensor_health=self.sanitize_sensor_health(sensor_health),
            recent_measurements=recent_list,
        )

    def build_prompts(self, context_dto: AIAnalysisContextDTO) -> tuple[str, str]:
        """Generate (system_prompt, user_prompt) pair."""
        lines = [
            f"ALERT TYPE: {context_dto.alert_type}",
            f"SEVERITY: {context_dto.severity}",
            f"DEVICE ID: {context_dto.device_id}",
        ]

        if context_dto.triggering_measurement:
            lines.append("TRIGGERING SENSOR MEASUREMENT:")
            for k, v in context_dto.triggering_measurement.items():
                if v is not None:
                    lines.append(f"  - {k}: {v}")
        else:
            lines.append("TRIGGERING SENSOR MEASUREMENT: None available")

        if context_dto.sensor_health:
            lines.append("HARDWARE SENSOR HEALTH:")
            for k, v in context_dto.sensor_health.items():
                if v is not None:
                    lines.append(f"  - {k}: {v}")

        if context_dto.recent_measurements:
            lines.append(f"RECENT SENSOR TRENDS ({len(context_dto.recent_measurements)} readings):")
            for idx, rm in enumerate(context_dto.recent_measurements, start=1):
                summary_items = [
                    f"{k}={v}" for k, v in rm.items() if v is not None and k not in ("timestamp",)
                ]
                lines.append(
                    f"  Reading {idx} ({rm.get('timestamp')}): {', '.join(summary_items[:6])}"
                )

        lines.append(
            "\nAnalyze the sensor readings objectively, check for possible hardware or positioning artifacts, "
            "and output strictly the required JSON object conforming to the system prompt instructions."
        )

        user_prompt = "\n".join(lines)
        return SYSTEM_PROMPT, user_prompt

    @staticmethod
    def create_fallback_enrichment(
        alert_type: str,
        severity: str,
        reason: str = "AI service unavailable",
    ) -> AIEnrichmentResult:
        """Produce a safe, deterministic fallback enrichment result when AI is unavailable or fails."""
        obs = [f"Alert triggered: {alert_type} with severity {severity}"]
        checks = ["Perform direct physical verification of the individual", "Inspect sensor status"]

        if "FALL" in alert_type.upper():
            summary = (
                "Deterministic fall anomaly triggered based on sensor acceleration thresholds."
            )
            obs.append("Acceleration magnitude exceeded configured threshold")
            factors = ["Sudden deceleration or impact", "Sensor displacement"]
            checks.append("Verify resident consciousness and mobility")
        elif "HEART" in alert_type.upper():
            summary = "Heart rate deviation detected outside configured safety boundaries."
            obs.append("Pulse rate sensor reading outside normal configured interval")
            factors = ["Physical exertion", "Sensor positioning or finger contact artifact"]
            checks.append("Verify sensor contact on finger/wrist")
        elif "TEMPERATURE" in alert_type.upper():
            summary = "Ambient or body temperature reading triggered threshold rule."
            factors = ["Environmental climate fluctuation", "Sensor proximity to heat source"]
        else:
            summary = f"Automated safety rule triggered for {alert_type} ({severity})."
            factors = ["Sensor threshold reached"]

        return AIEnrichmentResult(
            summary=summary,
            observations=obs,
            context=f"Deterministic fallback evaluation ({reason}).",
            confidence=0.70,
            data_quality="ACCEPTABLE",
            possible_factors=factors,
            recommended_checks=checks,
            limitations=[
                "Generated via deterministic rule engine fallback; advanced AI linguistic enrichment was offline.",
                "Non-diagnostic notification for caregiver operational awareness.",
            ],
        )
