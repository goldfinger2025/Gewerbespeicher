"""
API Key Management Endpoints
Third-party API access management
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models.user import User, UserRole
from app.models.api_key import API_SCOPES
from app.crud import api_key as api_key_crud
from app.crud import tenant as tenant_crud
from app.api.deps import get_current_user


router = APIRouter()


# ============ PYDANTIC MODELS ============

class APIKeyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    scopes: List[str]
    allowed_ips: Optional[List[str]] = None
    rate_limit_per_minute: int = 60
    rate_limit_per_day: int = 10000
    expires_at: Optional[datetime] = None


class APIKeyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scopes: Optional[List[str]] = None
    allowed_ips: Optional[List[str]] = None
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_day: Optional[int] = None
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    key_prefix: str
    scopes: List[str]
    allowed_ips: List[str]
    rate_limit_per_minute: int
    rate_limit_per_day: int
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyCreateResponse(APIKeyResponse):
    """Response when creating a new API key - includes the full key once"""
    api_key: str  # Full API key (only returned at creation!)


class ScopesResponse(BaseModel):
    scopes: dict


# ============ HELPER FUNCTIONS ============

def require_api_management_permission(user: User):
    """Require user to have permission to manage API keys"""
    if not user.is_admin and user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keine Berechtigung zur API-Key-Verwaltung"
        )


def validate_scopes(scopes: List[str]):
    """Validate that all requested scopes are valid"""
    valid_scopes = set(API_SCOPES.keys())
    for scope in scopes:
        if scope not in valid_scopes and scope != "*":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ungültiger Scope: {scope}"
            )


# ============ ENDPOINTS ============

@router.get("/scopes", response_model=ScopesResponse)
async def list_available_scopes():
    """
    List all available API scopes
    """
    return ScopesResponse(scopes=API_SCOPES)


@router.post("/", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new API key for the current tenant.

    IMPORTANT: The full API key is only returned once at creation!
    Store it securely - it cannot be retrieved later.
    """
    require_api_management_permission(current_user)

    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Benutzer ist keinem Tenant zugeordnet"
        )

    # Check if tenant has API enabled
    tenant = await tenant_crud.get_tenant_by_id(db, current_user.tenant_id)
    if not tenant or not tenant.api_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API-Zugang ist für diesen Tenant nicht aktiviert"
        )

    # Validate scopes
    validate_scopes(key_data.scopes)

    api_key, full_key = await api_key_crud.create_api_key(
        db=db,
        tenant_id=current_user.tenant_id,
        name=key_data.name,
        scopes=key_data.scopes,
        created_by_user_id=current_user.id,
        description=key_data.description,
        allowed_ips=key_data.allowed_ips,
        rate_limit_per_minute=key_data.rate_limit_per_minute,
        rate_limit_per_day=key_data.rate_limit_per_day,
        expires_at=key_data.expires_at,
    )

    return APIKeyCreateResponse(
        id=str(api_key.id),
        name=api_key.name,
        description=api_key.description,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        allowed_ips=api_key.allowed_ips or [],
        rate_limit_per_minute=int(api_key.rate_limit_per_minute),
        rate_limit_per_day=int(api_key.rate_limit_per_day),
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        usage_count=int(api_key.usage_count or 0),
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        api_key=full_key,  # Only returned at creation!
    )


@router.get("/", response_model=List[APIKeyResponse])
async def list_api_keys(
    include_revoked: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all API keys for the current tenant
    """
    require_api_management_permission(current_user)

    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Benutzer ist keinem Tenant zugeordnet"
        )

    keys = await api_key_crud.get_tenant_api_keys(
        db,
        tenant_id=current_user.tenant_id,
        include_revoked=include_revoked
    )

    return [
        APIKeyResponse(
            id=str(k.id),
            name=k.name,
            description=k.description,
            key_prefix=k.key_prefix,
            scopes=k.scopes or [],
            allowed_ips=k.allowed_ips or [],
            rate_limit_per_minute=int(k.rate_limit_per_minute),
            rate_limit_per_day=int(k.rate_limit_per_day),
            expires_at=k.expires_at,
            last_used_at=k.last_used_at,
            usage_count=int(k.usage_count or 0),
            is_active=k.is_active,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific API key
    """
    require_api_management_permission(current_user)

    api_key = await api_key_crud.get_api_key_by_id(db, key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API-Key nicht gefunden"
        )

    # Ensure key belongs to user's tenant
    if api_key.tenant_id != current_user.tenant_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kein Zugriff auf diesen API-Key"
        )

    return APIKeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        description=api_key.description,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes or [],
        allowed_ips=api_key.allowed_ips or [],
        rate_limit_per_minute=int(api_key.rate_limit_per_minute),
        rate_limit_per_day=int(api_key.rate_limit_per_day),
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        usage_count=int(api_key.usage_count or 0),
        is_active=api_key.is_active,
        created_at=api_key.created_at,
    )


@router.patch("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: UUID,
    update_data: APIKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update API key settings (not the key itself)
    """
    require_api_management_permission(current_user)

    api_key = await api_key_crud.get_api_key_by_id(db, key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API-Key nicht gefunden"
        )

    if api_key.tenant_id != current_user.tenant_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kein Zugriff auf diesen API-Key"
        )

    # Validate scopes if provided
    if update_data.scopes:
        validate_scopes(update_data.scopes)

    updated_key = await api_key_crud.update_api_key(
        db=db,
        api_key=api_key,
        **update_data.model_dump(exclude_unset=True)
    )

    return APIKeyResponse(
        id=str(updated_key.id),
        name=updated_key.name,
        description=updated_key.description,
        key_prefix=updated_key.key_prefix,
        scopes=updated_key.scopes or [],
        allowed_ips=updated_key.allowed_ips or [],
        rate_limit_per_minute=int(updated_key.rate_limit_per_minute),
        rate_limit_per_day=int(updated_key.rate_limit_per_day),
        expires_at=updated_key.expires_at,
        last_used_at=updated_key.last_used_at,
        usage_count=int(updated_key.usage_count or 0),
        is_active=updated_key.is_active,
        created_at=updated_key.created_at,
    )


@router.post("/{key_id}/regenerate", response_model=APIKeyCreateResponse)
async def regenerate_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate an API key (revokes old key and creates new one with same settings).

    IMPORTANT: The new API key is only returned once!
    Store it securely - it cannot be retrieved later.
    """
    require_api_management_permission(current_user)

    api_key = await api_key_crud.get_api_key_by_id(db, key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API-Key nicht gefunden"
        )

    if api_key.tenant_id != current_user.tenant_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kein Zugriff auf diesen API-Key"
        )

    new_key, full_key = await api_key_crud.regenerate_api_key(db, api_key)

    return APIKeyCreateResponse(
        id=str(new_key.id),
        name=new_key.name,
        description=new_key.description,
        key_prefix=new_key.key_prefix,
        scopes=new_key.scopes or [],
        allowed_ips=new_key.allowed_ips or [],
        rate_limit_per_minute=int(new_key.rate_limit_per_minute),
        rate_limit_per_day=int(new_key.rate_limit_per_day),
        expires_at=new_key.expires_at,
        last_used_at=new_key.last_used_at,
        usage_count=int(new_key.usage_count or 0),
        is_active=new_key.is_active,
        created_at=new_key.created_at,
        api_key=full_key,
    )


@router.post("/{key_id}/revoke", response_model=APIKeyResponse)
async def revoke_api_key(
    key_id: UUID,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke an API key
    """
    require_api_management_permission(current_user)

    api_key = await api_key_crud.get_api_key_by_id(db, key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API-Key nicht gefunden"
        )

    if api_key.tenant_id != current_user.tenant_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kein Zugriff auf diesen API-Key"
        )

    revoked_key = await api_key_crud.revoke_api_key(db, api_key, reason)

    return APIKeyResponse(
        id=str(revoked_key.id),
        name=revoked_key.name,
        description=revoked_key.description,
        key_prefix=revoked_key.key_prefix,
        scopes=revoked_key.scopes or [],
        allowed_ips=revoked_key.allowed_ips or [],
        rate_limit_per_minute=int(revoked_key.rate_limit_per_minute),
        rate_limit_per_day=int(revoked_key.rate_limit_per_day),
        expires_at=revoked_key.expires_at,
        last_used_at=revoked_key.last_used_at,
        usage_count=int(revoked_key.usage_count or 0),
        is_active=revoked_key.is_active,
        created_at=revoked_key.created_at,
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Permanently delete an API key
    """
    require_api_management_permission(current_user)

    api_key = await api_key_crud.get_api_key_by_id(db, key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API-Key nicht gefunden"
        )

    if api_key.tenant_id != current_user.tenant_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kein Zugriff auf diesen API-Key"
        )

    await api_key_crud.delete_api_key(db, api_key)
    return None
