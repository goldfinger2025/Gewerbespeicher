"""
Tenant Management Endpoints
Multi-Tenant and White-Label support
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
import re

from app.database import get_db
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.crud import tenant as tenant_crud
from app.api.deps import get_current_user


router = APIRouter()


# ============ PYDANTIC MODELS ============

class TenantCreate(BaseModel):
    name: str
    slug: str
    company_name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    subscription_plan: str = "starter"

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug darf nur Kleinbuchstaben, Zahlen und Bindestriche enthalten")
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Slug muss zwischen 3 und 50 Zeichen lang sein")
        return v


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    custom_domain: Optional[str] = None


class BrandingUpdate(BaseModel):
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    font_family: Optional[str] = None

    @field_validator("primary_color", "secondary_color", "accent_color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("Ungültiges Farbformat. Verwende Hex-Code (z.B. #2563eb)")
        return v


class FeaturesUpdate(BaseModel):
    features: dict


class LimitsUpdate(BaseModel):
    max_users: Optional[int] = None
    max_projects: Optional[int] = None
    max_storage_mb: Optional[int] = None


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    company_name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    custom_domain: Optional[str] = None
    subscription_plan: str
    subscription_status: str
    is_active: bool

    class Config:
        from_attributes = True


class TenantDetailResponse(TenantResponse):
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: str
    secondary_color: str
    accent_color: str
    font_family: str
    features: Optional[dict] = None
    max_users: int
    max_projects: int
    max_storage_mb: int
    api_enabled: bool
    api_rate_limit: int


class BrandingResponse(BaseModel):
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: str
    secondary_color: str
    accent_color: str
    font_family: str
    company_name: str


class LimitsResponse(BaseModel):
    users: dict
    projects: dict


# ============ HELPER FUNCTIONS ============

def require_tenant_owner(user: User, tenant: Tenant):
    """Require user to be tenant owner or system admin"""
    if not user.is_admin and (user.tenant_id != tenant.id or user.role != UserRole.OWNER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Tenant-Eigentümer können diese Aktion durchführen"
        )


def require_tenant_admin(user: User, tenant: Tenant):
    """Require user to be tenant admin or owner"""
    if not user.is_admin and (user.tenant_id != tenant.id or user.role not in [UserRole.OWNER, UserRole.ADMIN]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin-Rechte erforderlich"
        )


# ============ ENDPOINTS ============

@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new tenant (system admin only)
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur System-Administratoren können Tenants erstellen"
        )

    # Check if slug is unique
    existing = await tenant_crud.get_tenant_by_slug(db, tenant_data.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dieser Slug ist bereits vergeben"
        )

    tenant = await tenant_crud.create_tenant(
        db=db,
        name=tenant_data.name,
        slug=tenant_data.slug,
        company_name=tenant_data.company_name,
        email=tenant_data.email,
        phone=tenant_data.phone,
        address=tenant_data.address,
        postal_code=tenant_data.postal_code,
        city=tenant_data.city,
        subscription_plan=tenant_data.subscription_plan,
    )

    return TenantResponse(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        company_name=tenant.company_name,
        email=tenant.email,
        phone=tenant.phone,
        address=tenant.address,
        postal_code=tenant.postal_code,
        city=tenant.city,
        custom_domain=tenant.custom_domain,
        subscription_plan=tenant.subscription_plan,
        subscription_status=tenant.subscription_status,
        is_active=tenant.is_active,
    )


@router.get("/", response_model=List[TenantResponse])
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all tenants (system admin only)
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur System-Administratoren können alle Tenants sehen"
        )

    tenants = await tenant_crud.get_all_tenants(db, skip=skip, limit=limit)

    return [
        TenantResponse(
            id=str(t.id),
            name=t.name,
            slug=t.slug,
            company_name=t.company_name,
            email=t.email,
            phone=t.phone,
            address=t.address,
            postal_code=t.postal_code,
            city=t.city,
            custom_domain=t.custom_domain,
            subscription_plan=t.subscription_plan,
            subscription_status=t.subscription_status,
            is_active=t.is_active,
        )
        for t in tenants
    ]


@router.get("/current", response_model=TenantDetailResponse)
async def get_current_tenant(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's tenant details
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benutzer ist keinem Tenant zugeordnet"
        )

    tenant = await tenant_crud.get_tenant_by_id(db, current_user.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant nicht gefunden"
        )

    return TenantDetailResponse(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        company_name=tenant.company_name,
        email=tenant.email,
        phone=tenant.phone,
        address=tenant.address,
        postal_code=tenant.postal_code,
        city=tenant.city,
        custom_domain=tenant.custom_domain,
        subscription_plan=tenant.subscription_plan,
        subscription_status=tenant.subscription_status,
        is_active=tenant.is_active,
        logo_url=tenant.logo_url,
        favicon_url=tenant.favicon_url,
        primary_color=tenant.primary_color,
        secondary_color=tenant.secondary_color,
        accent_color=tenant.accent_color,
        font_family=tenant.font_family,
        features=tenant.features,
        max_users=int(tenant.max_users),
        max_projects=int(tenant.max_projects),
        max_storage_mb=int(tenant.max_storage_mb),
        api_enabled=tenant.api_enabled,
        api_rate_limit=int(tenant.api_rate_limit),
    )


@router.get("/{tenant_id}", response_model=TenantDetailResponse)
async def get_tenant(
    tenant_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get tenant by ID
    """
    tenant = await tenant_crud.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant nicht gefunden"
        )

    # Only allow access to own tenant or system admin
    if not current_user.is_admin and current_user.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kein Zugriff auf diesen Tenant"
        )

    return TenantDetailResponse(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        company_name=tenant.company_name,
        email=tenant.email,
        phone=tenant.phone,
        address=tenant.address,
        postal_code=tenant.postal_code,
        city=tenant.city,
        custom_domain=tenant.custom_domain,
        subscription_plan=tenant.subscription_plan,
        subscription_status=tenant.subscription_status,
        is_active=tenant.is_active,
        logo_url=tenant.logo_url,
        favicon_url=tenant.favicon_url,
        primary_color=tenant.primary_color,
        secondary_color=tenant.secondary_color,
        accent_color=tenant.accent_color,
        font_family=tenant.font_family,
        features=tenant.features,
        max_users=int(tenant.max_users),
        max_projects=int(tenant.max_projects),
        max_storage_mb=int(tenant.max_storage_mb),
        api_enabled=tenant.api_enabled,
        api_rate_limit=int(tenant.api_rate_limit),
    )


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    update_data: TenantUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update tenant settings (owner or system admin)
    """
    tenant = await tenant_crud.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant nicht gefunden"
        )

    require_tenant_owner(current_user, tenant)

    updated_tenant = await tenant_crud.update_tenant(
        db=db,
        tenant=tenant,
        **update_data.model_dump(exclude_unset=True)
    )

    return TenantResponse(
        id=str(updated_tenant.id),
        name=updated_tenant.name,
        slug=updated_tenant.slug,
        company_name=updated_tenant.company_name,
        email=updated_tenant.email,
        phone=updated_tenant.phone,
        address=updated_tenant.address,
        postal_code=updated_tenant.postal_code,
        city=updated_tenant.city,
        custom_domain=updated_tenant.custom_domain,
        subscription_plan=updated_tenant.subscription_plan,
        subscription_status=updated_tenant.subscription_status,
        is_active=updated_tenant.is_active,
    )


@router.put("/{tenant_id}/branding", response_model=BrandingResponse)
async def update_tenant_branding(
    tenant_id: UUID,
    branding_data: BrandingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update tenant branding (white-label settings)
    """
    tenant = await tenant_crud.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant nicht gefunden"
        )

    require_tenant_owner(current_user, tenant)

    updated_tenant = await tenant_crud.update_tenant_branding(
        db=db,
        tenant=tenant,
        **branding_data.model_dump(exclude_unset=True)
    )

    return BrandingResponse(
        logo_url=updated_tenant.logo_url,
        favicon_url=updated_tenant.favicon_url,
        primary_color=updated_tenant.primary_color,
        secondary_color=updated_tenant.secondary_color,
        accent_color=updated_tenant.accent_color,
        font_family=updated_tenant.font_family,
        company_name=updated_tenant.company_name,
    )


@router.get("/{tenant_id}/branding", response_model=BrandingResponse)
async def get_tenant_branding(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get tenant branding (public endpoint for white-label)
    """
    tenant = await tenant_crud.get_tenant_by_id(db, tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant nicht gefunden"
        )

    return BrandingResponse(
        logo_url=tenant.logo_url,
        favicon_url=tenant.favicon_url,
        primary_color=tenant.primary_color,
        secondary_color=tenant.secondary_color,
        accent_color=tenant.accent_color,
        font_family=tenant.font_family,
        company_name=tenant.company_name,
    )


@router.get("/by-slug/{slug}/branding", response_model=BrandingResponse)
async def get_tenant_branding_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get tenant branding by slug (public endpoint for white-label)
    """
    tenant = await tenant_crud.get_tenant_by_slug(db, slug)
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant nicht gefunden"
        )

    return BrandingResponse(
        logo_url=tenant.logo_url,
        favicon_url=tenant.favicon_url,
        primary_color=tenant.primary_color,
        secondary_color=tenant.secondary_color,
        accent_color=tenant.accent_color,
        font_family=tenant.font_family,
        company_name=tenant.company_name,
    )


@router.put("/{tenant_id}/features", response_model=dict)
async def update_tenant_features(
    tenant_id: UUID,
    features_data: FeaturesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update tenant feature flags (system admin only)
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur System-Administratoren können Features ändern"
        )

    tenant = await tenant_crud.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant nicht gefunden"
        )

    await tenant_crud.update_tenant_features(db, tenant, features_data.features)

    return {"features": tenant.features}


@router.get("/{tenant_id}/limits", response_model=LimitsResponse)
async def get_tenant_limits(
    tenant_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current resource usage and limits for tenant
    """
    tenant = await tenant_crud.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant nicht gefunden"
        )

    if not current_user.is_admin and current_user.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kein Zugriff auf diesen Tenant"
        )

    limits = await tenant_crud.check_tenant_limits(db, tenant)
    return LimitsResponse(**limits)


@router.put("/{tenant_id}/limits", response_model=dict)
async def update_tenant_limits(
    tenant_id: UUID,
    limits_data: LimitsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update tenant resource limits (system admin only)
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur System-Administratoren können Limits ändern"
        )

    tenant = await tenant_crud.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant nicht gefunden"
        )

    await tenant_crud.update_tenant_limits(
        db=db,
        tenant=tenant,
        max_users=limits_data.max_users,
        max_projects=limits_data.max_projects,
        max_storage_mb=limits_data.max_storage_mb,
    )

    return tenant.get_limits()


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a tenant (system admin only)
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur System-Administratoren können Tenants löschen"
        )

    tenant = await tenant_crud.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant nicht gefunden"
        )

    await tenant_crud.delete_tenant(db, tenant)
    return None
