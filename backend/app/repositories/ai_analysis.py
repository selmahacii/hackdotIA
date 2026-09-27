"""Repository for AIAnalysis domain entity."""

import uuid
from collections.abc import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analysis import AIAnalysis
from app.models.enums import AIAnalysisStatus, AIProvider
from app.repositories.base import BaseRepository


class AIAnalysisRepository(BaseRepository[AIAnalysis]):
    """Repository managing AIAnalysis database operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AIAnalysis, session)

    async def get_latest_by_alert_id(
        self, alert_id: uuid.UUID, provider: AIProvider | None = None
    ) -> AIAnalysis | None:
        """Fetch the most recent AIAnalysis record for a given alert."""
        stmt = select(AIAnalysis).where(AIAnalysis.alert_id == alert_id)
        if provider is not None:
            stmt = stmt.where(AIAnalysis.provider == provider)
        stmt = stmt.order_by(desc(AIAnalysis.created_at)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_alert_id(self, alert_id: uuid.UUID) -> Sequence[AIAnalysis]:
        """Fetch all AIAnalysis records for a given alert, descending by created_at."""
        stmt = (
            select(AIAnalysis)
            .where(AIAnalysis.alert_id == alert_id)
            .order_by(desc(AIAnalysis.created_at))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_or_completed_for_alert(
        self, alert_id: uuid.UUID, provider: AIProvider | None = None
    ) -> AIAnalysis | None:
        """Idempotency check: returns existing record if RUNNING, COMPLETED, or FALLBACK."""
        stmt = select(AIAnalysis).where(
            AIAnalysis.alert_id == alert_id,
            AIAnalysis.status.in_(
                [
                    AIAnalysisStatus.RUNNING,
                    AIAnalysisStatus.COMPLETED,
                    AIAnalysisStatus.FALLBACK,
                ]
            ),
        )
        if provider is not None:
            stmt = stmt.where(AIAnalysis.provider == provider)
        stmt = stmt.order_by(desc(AIAnalysis.created_at)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()
