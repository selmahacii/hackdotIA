import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.ai_analysis import AIAnalysis
from app.models.enums import AIAnalysisStatus, AIProvider
from app.schemas.ai_analysis import AIAnalysisAdminResponse, AIAnalysisCreate, AIAnalysisResponse


def test_ai_analysis_create_and_response() -> None:
    alert_id = uuid.uuid4()
    now = datetime.now(UTC)

    create_dto = AIAnalysisCreate(
        alert_id=alert_id,
        provider=AIProvider.NVIDIA,
        status=AIAnalysisStatus.COMPLETED,
        risk_level="HIGH",
        anomaly_detected=True,
        possible_event="fall_suspected",
        explanation="Accélération supérieure à 3g suivie d'immobilité.",
        recommended_action="Vérification sur place recommandée.",
        confidence=0.89,
        model_name="meta/llama-3.1-70b-instruct",
        latency_ms=250,
        raw_response={"model": "meta/llama-3.1-70b-instruct", "choices": []},
    )
    assert create_dto.confidence == 0.89
    assert create_dto.raw_response is not None

    # Public response does NOT contain raw_response
    resp = AIAnalysisResponse(
        id=uuid.uuid4(),
        alert_id=alert_id,
        provider=create_dto.provider,
        status=create_dto.status,
        risk_level=create_dto.risk_level,
        anomaly_detected=create_dto.anomaly_detected,
        possible_event=create_dto.possible_event,
        explanation=create_dto.explanation,
        recommended_action=create_dto.recommended_action,
        confidence=create_dto.confidence,
        model_name=create_dto.model_name,
        latency_ms=create_dto.latency_ms,
        created_at=now,
    )
    assert not hasattr(resp, "raw_response") or "raw_response" not in resp.model_fields


def test_ai_analysis_confidence_bounds() -> None:
    alert_id = uuid.uuid4()
    # Confidence > 1.0 must fail
    with pytest.raises(ValidationError):
        AIAnalysisCreate(
            alert_id=alert_id,
            confidence=1.1,
        )

    # Confidence < 0.0 must fail
    with pytest.raises(ValidationError):
        AIAnalysisCreate(
            alert_id=alert_id,
            confidence=-0.1,
        )


def test_ai_analysis_explanation_length_limit() -> None:
    alert_id = uuid.uuid4()
    # Explanation > 500 chars must fail
    too_long = "a" * 501
    with pytest.raises(ValidationError):
        AIAnalysisCreate(
            alert_id=alert_id,
            explanation=too_long,
        )

    # Explanation <= 500 chars must succeed
    valid_long = "a" * 500
    dto = AIAnalysisCreate(
        alert_id=alert_id,
        explanation=valid_long,
    )
    assert len(dto.explanation or "") == 500


def test_sqlalchemy_to_pydantic_response_from_attributes() -> None:
    now = datetime.now(UTC)
    analysis_id = uuid.uuid4()
    alert_id = uuid.uuid4()

    # Create real SQLAlchemy model instance
    sql_model = AIAnalysis(
        id=analysis_id,
        alert_id=alert_id,
        provider=AIProvider.NVIDIA,
        status=AIAnalysisStatus.COMPLETED,
        risk_level="MEDIUM",
        anomaly_detected=True,
        possible_event="heart_rate_spike",
        explanation="Rythme cardiaque à 145 bpm au repos.",
        recommended_action="Vérifier l'état de stress ou d'effort.",
        confidence=0.82,
        model_name="meta/llama-3.1-70b-instruct",
        latency_ms=310,
        created_at=now,
        raw_response={"internal_metric": 42},
    )

    # Convert using from_attributes=True
    pydantic_resp = AIAnalysisResponse.model_validate(sql_model)
    assert pydantic_resp.id == analysis_id
    assert pydantic_resp.confidence == 0.82
    assert pydantic_resp.possible_event == "heart_rate_spike"

    # Convert to admin response
    admin_resp = AIAnalysisAdminResponse.model_validate(sql_model)
    assert admin_resp.raw_response == {"internal_metric": 42}
