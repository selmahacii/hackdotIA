"""Admin API endpoints for user management and system metrics."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.core.security import hash_password
from app.models.alert import Alert
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import AlertStatus, DeviceStatus, UserRole
from app.models.measurement import Measurement
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
async def list_users(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN"]))],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> dict:
    """List users with pagination and role filters (Admin and Superadmin only)."""
    user_repo = UserRepository(session)
    users, total = await user_repo.list_users(
        skip=skip, limit=limit, role=role, is_active=is_active
    )

    items = [
        {
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "is_active": u.is_active,
            "assigned_elderly_ids": u.assigned_elderly_ids,
            "created_at": u.created_at.isoformat(),
            "updated_at": u.updated_at.isoformat(),
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        }
        for u in users
    ]

    return {
        "items": items,
        "total": total,
        "page": (skip // limit) + 1,
        "page_size": limit,
    }


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN"]))],
) -> dict:
    """Create a new user account (Admin and Superadmin only)."""
    # Only SUPERADMIN can create SUPERADMIN
    if user_in.role == UserRole.SUPERADMIN and current_user.role != "SUPERADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un Superadmin peut créer un compte Superadmin",
        )

    user_repo = UserRepository(session)

    # Check for existing email or username
    existing_email = await user_repo.get_by_email(user_in.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une adresse email identique existe déjà",
        )

    existing_username = await user_repo.get_by_username(user_in.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un nom d'utilisateur identique existe déjà",
        )

    hashed = hash_password(user_in.password)
    user = await user_repo.create_user(user_in, hashed)
    await session.commit()

    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "is_active": user.is_active,
        "assigned_elderly_ids": user.assigned_elderly_ids,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


@router.get("/users/{user_id}")
async def get_user_by_id(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN"]))],
) -> dict:
    """Retrieve user details by ID."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé",
        )

    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "is_active": user.is_active,
        "assigned_elderly_ids": user.assigned_elderly_ids,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN"]))],
) -> dict:
    """Update user information (Admin and Superadmin only)."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé",
        )

    # Only SUPERADMIN can modify a SUPERADMIN or promote to SUPERADMIN
    if (
        user.role == UserRole.SUPERADMIN or user_in.role == UserRole.SUPERADMIN
    ) and current_user.role != "SUPERADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un Superadmin peut modifier le rôle Superadmin",
        )

    hashed: str | None = None
    if user_in.password:
        hashed = hash_password(user_in.password)

    updated_user = await user_repo.update_user(user, user_in, hashed_password=hashed)
    await session.commit()

    return {
        "id": str(updated_user.id),
        "username": updated_user.username,
        "email": updated_user.email,
        "full_name": updated_user.full_name,
        "role": (
            updated_user.role.value
            if hasattr(updated_user.role, "value")
            else str(updated_user.role)
        ),
        "is_active": updated_user.is_active,
        "assigned_elderly_ids": updated_user.assigned_elderly_ids,
        "created_at": updated_user.created_at.isoformat(),
        "updated_at": updated_user.updated_at.isoformat(),
        "last_login_at": (
            updated_user.last_login_at.isoformat() if updated_user.last_login_at else None
        ),
    }


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["SUPERADMIN"]))],
) -> None:
    """Delete a user account (Superadmin only)."""
    if str(user_id) == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer son propre compte administrateur",
        )

    user_repo = UserRepository(session)
    deleted = await user_repo.delete(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé",
        )
    await session.commit()


@router.get("/stats")
async def get_admin_stats(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN"]))],
) -> dict:
    """Retrieve system and tenant statistics."""
    # Count users
    total_users_res = await session.execute(select(func.count(User.id)))
    total_users = total_users_res.scalar() or 0

    # User role distribution
    roles_res = await session.execute(select(User.role, func.count(User.id)).group_by(User.role))
    role_dist = {str(r[0].value if hasattr(r[0], "value") else r[0]): r[1] for r in roles_res.all()}

    # Residents count
    elderly_count_res = await session.execute(select(func.count(ElderlyPerson.id)))
    elderly_count = elderly_count_res.scalar() or 0

    # Devices count
    devices_count_res = await session.execute(select(func.count(Device.id)))
    devices_count = devices_count_res.scalar() or 0

    # Online devices count
    online_devices_res = await session.execute(
        select(func.count(Device.id)).where(Device.status == DeviceStatus.ONLINE)
    )
    online_devices = online_devices_res.scalar() or 0

    # Alerts count
    open_alerts_res = await session.execute(
        select(func.count(Alert.id)).where(Alert.status == AlertStatus.OPEN)
    )
    open_alerts = open_alerts_res.scalar() or 0

    # Total measurements
    measurements_count_res = await session.execute(select(func.count(Measurement.id)))
    total_measurements = measurements_count_res.scalar() or 0

    return {
        "users": {
            "total": total_users,
            "by_role": role_dist,
        },
        "residents": elderly_count,
        "devices": {
            "total": devices_count,
            "online": online_devices,
            "offline": devices_count - online_devices,
        },
        "alerts": {
            "open": open_alerts,
        },
        "measurements": {
            "total": total_measurements,
        },
        "system_status": "OPERATIONAL",
    }


@router.get("/rbac/matrix")
async def get_rbac_matrix(
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN"]))],
) -> dict:
    """Return complete RBAC role definitions, hierarchy, and permissions matrix."""
    roles = [
        {
            "role": "SUPERADMIN",
            "name": "Super Administrateur",
            "level": 1,
            "badge_variant": "danger",
            "description": "Contrôle souverain de la plateforme, gestion des administrateurs, suppression de comptes et accès système global.",
            "target_persona": "Responsable Technique / RSSI / DevOps",
            "caregiver_isolation": False,
            "can_delete_users": True,
            "can_manage_admins": True,
        },
        {
            "role": "ADMIN",
            "name": "Administrateur Établissement",
            "level": 2,
            "badge_variant": "purple",
            "description": "Supervision globale de l'EHPAD, création des soignants et opérateurs, affectation des résidents et gestion des capteurs.",
            "target_persona": "Direction Médicale / Cadre de Santé / Chef de Service",
            "caregiver_isolation": False,
            "can_delete_users": False,
            "can_manage_admins": False,
        },
        {
            "role": "CAREGIVER",
            "name": "Soignant / Infirmier",
            "level": 3,
            "badge_variant": "primary",
            "description": "Accès clinique ciblé avec cloisonnement strict (Row-Level Security) : accès restreint uniquement aux résidents affectés.",
            "target_persona": "Infirmier(ère) / Aide-Soignant(e) / Médecin traitant",
            "caregiver_isolation": True,
            "can_delete_users": False,
            "can_manage_admins": False,
        },
        {
            "role": "OPERATOR",
            "name": "Opérateur de Surveillance",
            "level": 3,
            "badge_variant": "warning",
            "description": "Monitoring temps réel des constantes vitales, levée de doute, acquittement initial des alertes d'urgence 24/7.",
            "target_persona": "Poste de Garde / Téléassistance / PC Sécurité",
            "caregiver_isolation": False,
            "can_delete_users": False,
            "can_manage_admins": False,
        },
        {
            "role": "READ_ONLY",
            "name": "Auditeur / Lecture Seule",
            "level": 4,
            "badge_variant": "neutral",
            "description": "Consultation passive des indicateurs d'établissement, statistiques agrégées et rapports sans droit de modification.",
            "target_persona": "Inspecteur ARS / Famille tuteur / Auditeur qualité",
            "caregiver_isolation": False,
            "can_delete_users": False,
            "can_manage_admins": False,
        },
    ]

    modules = [
        {
            "category": "Surveillance & Constantes Vitales",
            "permissions": [
                {
                    "code": "DASHBOARD_VIEW",
                    "label": "Accès Tableau de Bord Global",
                    "description": "Visualiser les KPI globaux, nombre de résidents, état de santé général.",
                    "roles": ["SUPERADMIN", "ADMIN", "CAREGIVER", "OPERATOR", "READ_ONLY"],
                },
                {
                    "code": "TELEMETRY_REALTIME",
                    "label": "Flux Télémétrie Live (25 Hz / 1 Hz)",
                    "description": "Réception en temps réel des flux WebSocket (BPM, SpO2, accélération 3D, GPS).",
                    "roles": ["SUPERADMIN", "ADMIN", "CAREGIVER", "OPERATOR"],
                },
                {
                    "code": "MEASUREMENTS_HISTORY",
                    "label": "Historique & Courbes Physiologiques",
                    "description": "Consultation des séries temporelles et export des tendances physiologiques.",
                    "roles": ["SUPERADMIN", "ADMIN", "CAREGIVER", "OPERATOR", "READ_ONLY"],
                },
            ],
        },
        {
            "category": "Alertes & Urgences Médicales",
            "permissions": [
                {
                    "code": "ALERTS_VIEW",
                    "label": "Consultation des Alertes",
                    "description": "Accès à la liste des alertes et incidents physiologiques (filtré selon affectation pour soignants).",
                    "roles": ["SUPERADMIN", "ADMIN", "CAREGIVER", "OPERATOR", "READ_ONLY"],
                },
                {
                    "code": "ALERTS_ACKNOWLEDGE",
                    "label": "Prise en charge / Acquittement (ACK)",
                    "description": "Marquer une alerte critique comme prise en charge par un soignant ou opérateur.",
                    "roles": ["SUPERADMIN", "ADMIN", "CAREGIVER", "OPERATOR"],
                },
                {
                    "code": "ALERTS_RESOLVE",
                    "label": "Résolution & Clôture d'Incidents",
                    "description": "Consigner les actions thérapeutiques menées et clôturer l'incident médical.",
                    "roles": ["SUPERADMIN", "ADMIN", "CAREGIVER"],
                },
            ],
        },
        {
            "category": "Intelligence Artificielle & Diagnostic Groq",
            "permissions": [
                {
                    "code": "AI_DIAGNOSTICS_VIEW",
                    "label": "Lecture Diagnostics Différentiels IA",
                    "description": "Accès aux analyses contextuelles, scores de risque et recommandations cliniques générées par Groq LLM.",
                    "roles": ["SUPERADMIN", "ADMIN", "CAREGIVER", "OPERATOR"],
                },
                {
                    "code": "AI_REEVALUATION_TRIGGER",
                    "label": "Déclenchement Manuel Ré-analyse IA",
                    "description": "Forcer une nouvelle analyse approfondie Groq sur une alerte ou série de mesures suspectes.",
                    "roles": ["SUPERADMIN", "ADMIN", "CAREGIVER"],
                },
            ],
        },
        {
            "category": "Gestion des Résidents & Dossiers",
            "permissions": [
                {
                    "code": "RESIDENTS_VIEW",
                    "label": "Consultation Dossier Résident",
                    "description": "Visualiser l'identité, antécédents, contacts d'urgence (scopé par affectation pour soignants).",
                    "roles": ["SUPERADMIN", "ADMIN", "CAREGIVER", "OPERATOR", "READ_ONLY"],
                },
                {
                    "code": "RESIDENTS_MANAGE",
                    "label": "Création / Modification Dossiers",
                    "description": "Ajouter un nouveau résident, éditer les fiches médicales et contacts d'urgence.",
                    "roles": ["SUPERADMIN", "ADMIN"],
                },
                {
                    "code": "CAREGIVER_ASSIGNMENT",
                    "label": "Affectation Soignants - Résidents",
                    "description": "Définir le périmètre de prise en charge et le cloisonnement des données pour les soignants.",
                    "roles": ["SUPERADMIN", "ADMIN"],
                },
            ],
        },
        {
            "category": "Appareils IoT & Intégrité Capteurs",
            "permissions": [
                {
                    "code": "DEVICES_VIEW",
                    "label": "Inventaire & Diagnostic Capteurs",
                    "description": "Consultation du statut matériel (MPU6050, MAX30102, DHT11, GPS, batterie, RSSI).",
                    "roles": ["SUPERADMIN", "ADMIN", "CAREGIVER", "OPERATOR", "READ_ONLY"],
                },
                {
                    "code": "DEVICES_PROVISION",
                    "label": "Provisioning & Association Bracelets",
                    "description": "Enregistrer un nouveau bracelet ESP32, lier à un résident ou modifier la configuration.",
                    "roles": ["SUPERADMIN", "ADMIN"],
                },
            ],
        },
        {
            "category": "Gouvernance, RBAC & Sécurité",
            "permissions": [
                {
                    "code": "USERS_VIEW",
                    "label": "Annuaire des Utilisateurs",
                    "description": "Consulter les comptes utilisateurs, rôles attribués et statut de connexion.",
                    "roles": ["SUPERADMIN", "ADMIN"],
                },
                {
                    "code": "USERS_MANAGE",
                    "label": "Gestion des Comptes & Mots de Passe",
                    "description": "Créer des comptes, réinitialiser des mots de passe, activer ou désactiver un accès.",
                    "roles": ["SUPERADMIN", "ADMIN"],
                },
                {
                    "code": "SUPERADMIN_OPS",
                    "label": "Opérations Superadmin & Audit",
                    "description": "Suppression définitive de compte, promotion Superadmin, purge et métriques système.",
                    "roles": ["SUPERADMIN"],
                },
            ],
        },
    ]

    policies = {
        "caregiver_isolation_mode": "STRICT_ROW_LEVEL_SECURITY",
        "caregiver_scope_rule": (
            "Un utilisateur de rôle CAREGIVER ne peut voir que les alertes et résidents dont "
            "l'identifiant figure dans 'assigned_elderly_ids'. Si la liste est vide, aucun accès "
            "aux données personnelles de résidents n'est accordé."
        ),
        "token_algorithm": "HS256",
        "token_ttl_minutes": 480,
        "least_privilege_enforced": True,
    }

    return {
        "roles": roles,
        "modules": modules,
        "policies": policies,
    }
