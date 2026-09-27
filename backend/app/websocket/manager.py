"""WebSocket connection manager for real-time frontend notifications."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts structured real-time events."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "WebSocket client connected. Total connections: %d", len(self.active_connections)
        )

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                "WebSocket client disconnected. Total connections: %d", len(self.active_connections)
            )

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Broadcast a schema-versioned event envelope to all connected clients."""
        envelope = {
            "schema_version": "1.0",
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data,
        }

        stale_connections = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(envelope)
            except Exception as exc:
                logger.warning(
                    "Failed to send WebSocket message: %s. Marking connection as stale.", exc
                )
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(connection)

    async def broadcast_ai_analysis_completed(
        self,
        alert_id: uuid.UUID,
        analysis_id: uuid.UUID,
        status: str,
        risk_level: str | None = None,
        confidence: float | None = None,
        summary: str | None = None,
        recommended_action: str | None = None,
    ) -> None:
        """Convenience method to broadcast ai.analysis.completed event."""
        payload = {
            "alert_id": str(alert_id),
            "analysis_id": str(analysis_id),
            "status": status,
            "risk_level": risk_level,
            "confidence": confidence,
            "summary": summary,
            "recommended_action": recommended_action,
        }
        await self.broadcast(event_type="ai.analysis.completed", data=payload)


ws_manager = ConnectionManager()
