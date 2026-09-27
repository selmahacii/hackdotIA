"""API Dependencies including database sessions and RBAC authentication."""

import logging
import uuid
from collections.abc import AsyncGenerator, Callable, Coroutine, Sequence
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.alert import Alert

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    """Authenticated user context for API endpoints."""

    id: str
    username: str
    role: str  # ADMIN, CAREGIVER, OPERATOR, READ_ONLY
    assigned_elderly_ids: list[uuid.UUID] = Field(default_factory=list)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(security_scheme)],
) -> AuthenticatedUser:
    """Decode and validate Bearer JWT token from request authorization header."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except Exception as exc:
        logger.warning("JWT verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    sub: str = payload.get("sub", "")
    role: str = payload.get("role", "READ_ONLY").upper()
    assigned_raw = payload.get("assigned_elderly_ids", [])
    assigned_ids: list[uuid.UUID] = []
    if isinstance(assigned_raw, list):
        for item in assigned_raw:
            try:
                assigned_ids.append(uuid.UUID(str(item)))
            except ValueError:
                pass

    return AuthenticatedUser(
        id=payload.get("user_id", sub),
        username=sub,
        role=role,
        assigned_elderly_ids=assigned_ids,
    )


def require_roles(
    allowed_roles: Sequence[str],
) -> Callable[[AuthenticatedUser], Coroutine[Any, Any, AuthenticatedUser]]:
    """Enforce role-based access control (RBAC)."""
    allowed_upper = {r.upper() for r in allowed_roles}

    async def role_checker(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if current_user.role != "SUPERADMIN" and current_user.role not in allowed_upper:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role '{current_user.role}'. Required: {sorted(allowed_upper)}",
            )
        return current_user

    return role_checker


def check_alert_caregiver_access(alert: Alert, user: AuthenticatedUser) -> None:
    """Check caregiver isolation: if user is CAREGIVER and has assigned elderly, enforce restriction."""
    if user.role == "CAREGIVER" and user.assigned_elderly_ids:
        if alert.elderly_id is None or alert.elderly_id not in user.assigned_elderly_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Caregiver is not authorized to access alerts for this resident",
            )


def check_elderly_caregiver_access(elderly_id: uuid.UUID, user: AuthenticatedUser) -> None:
    """Check caregiver isolation on resident endpoint."""
    if user.role == "CAREGIVER" and user.assigned_elderly_ids:
        if elderly_id not in user.assigned_elderly_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Caregiver is not authorized to access this resident",
            )


__all__ = [
    "get_db",
    "AsyncGenerator",
    "AsyncSession",
    "AuthenticatedUser",
    "get_current_user",
    "require_roles",
    "check_alert_caregiver_access",
    "check_elderly_caregiver_access",
]
