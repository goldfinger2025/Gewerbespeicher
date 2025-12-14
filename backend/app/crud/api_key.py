"""
API Key CRUD Operations
Database operations for API keys (third-party access)
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone
import hashlib
import secrets

from app.models.api_key import APIKey


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key with prefix and hash.
    Returns: (full_key, key_prefix, key_hash)
    """
    raw_key = secrets.token_urlsafe(32)
    full_key = f"gsp_{raw_key}"
    key_prefix = full_key[:12]  # "gsp_" + first 8 chars
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, key_prefix, key_hash


def hash_api_key(key: str) -> str:
    """Hash an API key for storage"""
    return hashlib.sha256(key.encode()).hexdigest()


async def get_api_key_by_id(db: AsyncSession, key_id: UUID) -> Optional[APIKey]:
    """Get an API key by ID"""
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id)
    )
    return result.scalar_one_or_none()


async def get_api_key_by_hash(db: AsyncSession, key_hash: str) -> Optional[APIKey]:
    """Get an API key by its hash"""
    result = await db.execute(
        select(APIKey).where(APIKey.key_hash == key_hash)
    )
    return result.scalar_one_or_none()


async def validate_api_key(db: AsyncSession, api_key: str) -> Optional[APIKey]:
    """
    Validate an API key and return the key object if valid.
    Also updates last_used_at and usage_count.
    """
    key_hash = hash_api_key(api_key)
    key = await get_api_key_by_hash(db, key_hash)

    if key and key.is_valid:
        # Update usage stats
        key.last_used_at = datetime.now(timezone.utc)
        key.usage_count = (key.usage_count or 0) + 1
        await db.flush()
        return key

    return None


async def get_tenant_api_keys(
    db: AsyncSession,
    tenant_id: UUID,
    include_revoked: bool = False
) -> List[APIKey]:
    """Get all API keys for a tenant"""
    query = select(APIKey).where(APIKey.tenant_id == tenant_id)
    if not include_revoked:
        query = query.where(APIKey.revoked_at.is_(None))
    query = query.order_by(APIKey.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_api_key(
    db: AsyncSession,
    tenant_id: UUID,
    name: str,
    scopes: List[str],
    created_by_user_id: Optional[UUID] = None,
    description: Optional[str] = None,
    allowed_ips: Optional[List[str]] = None,
    rate_limit_per_minute: int = 60,
    rate_limit_per_day: int = 10000,
    expires_at: Optional[datetime] = None,
) -> tuple[APIKey, str]:
    """
    Create a new API key.
    Returns: (APIKey object, full_key_string)
    Note: The full key is only returned once at creation time!
    """
    full_key, key_prefix, key_hash = generate_api_key()

    api_key = APIKey(
        tenant_id=tenant_id,
        created_by_user_id=created_by_user_id,
        name=name,
        description=description,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=scopes,
        allowed_ips=allowed_ips or [],
        rate_limit_per_minute=rate_limit_per_minute,
        rate_limit_per_day=rate_limit_per_day,
        expires_at=expires_at,
    )

    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)

    return api_key, full_key


async def update_api_key(
    db: AsyncSession,
    api_key: APIKey,
    name: Optional[str] = None,
    description: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    allowed_ips: Optional[List[str]] = None,
    rate_limit_per_minute: Optional[int] = None,
    rate_limit_per_day: Optional[int] = None,
    expires_at: Optional[datetime] = None,
) -> APIKey:
    """Update API key settings (not the key itself)"""
    if name is not None:
        api_key.name = name
    if description is not None:
        api_key.description = description
    if scopes is not None:
        api_key.scopes = scopes
    if allowed_ips is not None:
        api_key.allowed_ips = allowed_ips
    if rate_limit_per_minute is not None:
        api_key.rate_limit_per_minute = rate_limit_per_minute
    if rate_limit_per_day is not None:
        api_key.rate_limit_per_day = rate_limit_per_day
    if expires_at is not None:
        api_key.expires_at = expires_at

    await db.flush()
    await db.refresh(api_key)
    return api_key


async def revoke_api_key(
    db: AsyncSession,
    api_key: APIKey,
    reason: Optional[str] = None
) -> APIKey:
    """Revoke an API key"""
    api_key.is_active = False
    api_key.revoked_at = datetime.now(timezone.utc)
    api_key.revoked_reason = reason
    await db.flush()
    await db.refresh(api_key)
    return api_key


async def delete_api_key(db: AsyncSession, api_key: APIKey) -> None:
    """Permanently delete an API key"""
    await db.delete(api_key)
    await db.flush()


async def get_active_key_count(db: AsyncSession, tenant_id: UUID) -> int:
    """Get count of active API keys for a tenant"""
    result = await db.execute(
        select(func.count(APIKey.id))
        .where(APIKey.tenant_id == tenant_id)
        .where(APIKey.is_active == True)
        .where(APIKey.revoked_at.is_(None))
    )
    return result.scalar() or 0


async def regenerate_api_key(
    db: AsyncSession,
    old_key: APIKey
) -> tuple[APIKey, str]:
    """
    Regenerate an API key (revoke old, create new with same settings).
    Returns: (new APIKey object, new full_key_string)
    """
    # Revoke old key
    await revoke_api_key(db, old_key, reason="Regenerated")

    # Create new key with same settings
    return await create_api_key(
        db=db,
        tenant_id=old_key.tenant_id,
        name=old_key.name,
        scopes=old_key.scopes,
        created_by_user_id=old_key.created_by_user_id,
        description=old_key.description,
        allowed_ips=old_key.allowed_ips,
        rate_limit_per_minute=old_key.rate_limit_per_minute,
        rate_limit_per_day=old_key.rate_limit_per_day,
        expires_at=old_key.expires_at,
    )
