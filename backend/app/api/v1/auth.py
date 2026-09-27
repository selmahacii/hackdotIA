"""Authentication API endpoints for login and user context."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthenticatedUser, get_current_user, get_db
from app.config import settings
from app.core.security import create_access_token, verify_password
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    login_data: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Authenticate user with username and password, returning JWT access token."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_username(login_data.username)

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte utilisateur est désactivé",
        )

    # Update last login timestamp
    await user_repo.update_last_login(user)
    await session.commit()

    token_data = {
        "sub": user.username,
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "assigned_elderly_ids": user.assigned_elderly_ids,
    }

    access_token = create_access_token(token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.JWT_EXPIRE_MINUTES * 60,
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "assigned_elderly_ids": user.assigned_elderly_ids,
        },
    }


@router.get("/me")
async def get_me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Return the profile of the currently authenticated user."""
    user_repo = UserRepository(session)
    try:
        user_uuid = uuid.UUID(current_user.id)
        user = await user_repo.get_by_id(user_uuid)
    except (ValueError, TypeError):
        user = await user_repo.get_by_username(current_user.username)

    if user:
        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "is_active": user.is_active,
            "assigned_elderly_ids": user.assigned_elderly_ids,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        }

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": f"{current_user.username}@smartelderly.local",
        "full_name": current_user.username.capitalize(),
        "role": current_user.role,
        "is_active": True,
        "assigned_elderly_ids": [str(eid) for eid in current_user.assigned_elderly_ids],
    }
