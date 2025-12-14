"""
Tenant CRUD Operations
Database operations for tenants (multi-tenant support)
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID

from app.models.tenant import Tenant
from app.models.user import User


async def get_tenant_by_id(db: AsyncSession, tenant_id: UUID) -> Optional[Tenant]:
    """Get a tenant by ID"""
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    return result.scalar_one_or_none()


async def get_tenant_by_slug(db: AsyncSession, slug: str) -> Optional[Tenant]:
    """Get a tenant by slug"""
    result = await db.execute(
        select(Tenant).where(Tenant.slug == slug)
    )
    return result.scalar_one_or_none()


async def get_tenant_by_domain(db: AsyncSession, domain: str) -> Optional[Tenant]:
    """Get a tenant by custom domain"""
    result = await db.execute(
        select(Tenant).where(Tenant.custom_domain == domain)
    )
    return result.scalar_one_or_none()


async def get_all_tenants(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False
) -> List[Tenant]:
    """Get all tenants with pagination"""
    query = select(Tenant)
    if not include_inactive:
        query = query.where(Tenant.is_active == True)
    query = query.offset(skip).limit(limit).order_by(Tenant.name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_tenant(
    db: AsyncSession,
    name: str,
    slug: str,
    company_name: str,
    email: str,
    **kwargs
) -> Tenant:
    """Create a new tenant"""
    tenant = Tenant(
        name=name,
        slug=slug,
        company_name=company_name,
        email=email,
        **kwargs
    )
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)
    return tenant


async def update_tenant(
    db: AsyncSession,
    tenant: Tenant,
    **kwargs
) -> Tenant:
    """Update tenant fields"""
    for key, value in kwargs.items():
        if hasattr(tenant, key) and value is not None:
            setattr(tenant, key, value)
    await db.flush()
    await db.refresh(tenant)
    return tenant


async def update_tenant_branding(
    db: AsyncSession,
    tenant: Tenant,
    logo_url: Optional[str] = None,
    favicon_url: Optional[str] = None,
    primary_color: Optional[str] = None,
    secondary_color: Optional[str] = None,
    accent_color: Optional[str] = None,
    font_family: Optional[str] = None,
) -> Tenant:
    """Update tenant branding (white-label)"""
    if logo_url is not None:
        tenant.logo_url = logo_url
    if favicon_url is not None:
        tenant.favicon_url = favicon_url
    if primary_color is not None:
        tenant.primary_color = primary_color
    if secondary_color is not None:
        tenant.secondary_color = secondary_color
    if accent_color is not None:
        tenant.accent_color = accent_color
    if font_family is not None:
        tenant.font_family = font_family
    await db.flush()
    await db.refresh(tenant)
    return tenant


async def update_tenant_features(
    db: AsyncSession,
    tenant: Tenant,
    features: dict
) -> Tenant:
    """Update tenant feature flags"""
    tenant.features = features
    await db.flush()
    await db.refresh(tenant)
    return tenant


async def update_tenant_limits(
    db: AsyncSession,
    tenant: Tenant,
    max_users: Optional[int] = None,
    max_projects: Optional[int] = None,
    max_storage_mb: Optional[int] = None,
) -> Tenant:
    """Update tenant resource limits"""
    if max_users is not None:
        tenant.max_users = max_users
    if max_projects is not None:
        tenant.max_projects = max_projects
    if max_storage_mb is not None:
        tenant.max_storage_mb = max_storage_mb
    await db.flush()
    await db.refresh(tenant)
    return tenant


async def deactivate_tenant(db: AsyncSession, tenant: Tenant) -> Tenant:
    """Deactivate a tenant (soft delete)"""
    tenant.is_active = False
    await db.flush()
    await db.refresh(tenant)
    return tenant


async def delete_tenant(db: AsyncSession, tenant: Tenant) -> None:
    """Permanently delete a tenant and all associated data"""
    await db.delete(tenant)
    await db.flush()


async def get_tenant_user_count(db: AsyncSession, tenant_id: UUID) -> int:
    """Get number of users in a tenant"""
    result = await db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant_id)
    )
    return result.scalar() or 0


async def get_tenant_with_users(db: AsyncSession, tenant_id: UUID) -> Optional[Tenant]:
    """Get a tenant with all users eagerly loaded"""
    result = await db.execute(
        select(Tenant)
        .options(selectinload(Tenant.users))
        .where(Tenant.id == tenant_id)
    )
    return result.scalar_one_or_none()


async def check_tenant_limits(db: AsyncSession, tenant: Tenant) -> dict:
    """Check if tenant is within resource limits"""
    from app.models.project import Project

    user_count = await db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant.id)
    )
    project_count = await db.execute(
        select(func.count(Project.id))
        .join(User)
        .where(User.tenant_id == tenant.id)
    )

    users = user_count.scalar() or 0
    projects = project_count.scalar() or 0

    return {
        "users": {
            "current": users,
            "max": tenant.max_users,
            "exceeded": users >= tenant.max_users
        },
        "projects": {
            "current": projects,
            "max": tenant.max_projects,
            "exceeded": projects >= tenant.max_projects
        }
    }
