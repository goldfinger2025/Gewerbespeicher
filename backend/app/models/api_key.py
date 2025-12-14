"""
API Key Model
SQLAlchemy ORM model for third-party API access
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
import secrets

from app.database import Base


def generate_api_key() -> str:
    """Generate a secure API key with prefix"""
    return f"gsp_{secrets.token_urlsafe(32)}"


class APIKey(Base):
    """API Key model for third-party integrations"""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)

    # Key Details
    name = Column(String(255), nullable=False)  # Human-readable name
    description = Column(Text)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)  # Hashed API key
    key_prefix = Column(String(20), nullable=False)  # First chars for identification (e.g., "gsp_abc...")

    # Permissions
    scopes = Column(JSONB, default=list)  # ["projects:read", "simulations:write", ...]
    allowed_ips = Column(JSONB, default=list)  # IP whitelist (empty = all allowed)

    # Rate Limiting
    rate_limit_per_minute = Column(Float, default=60)
    rate_limit_per_day = Column(Float, default=10000)

    # Usage Tracking
    last_used_at = Column(DateTime)
    usage_count = Column(Float, default=0)

    # Expiration
    expires_at = Column(DateTime)  # null = never expires

    # Status
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime)
    revoked_reason = Column(String(255))

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey {self.name} ({self.key_prefix}...)>"

    @property
    def is_valid(self) -> bool:
        """Check if API key is valid and not expired"""
        from datetime import datetime, timezone

        if not self.is_active:
            return False
        if self.revoked_at:
            return False
        if self.expires_at and self.expires_at < datetime.now(timezone.utc):
            return False
        return True

    def has_scope(self, scope: str) -> bool:
        """Check if API key has a specific scope"""
        if not self.scopes:
            return False
        # Check for exact match or wildcard
        if scope in self.scopes:
            return True
        # Check for wildcard (e.g., "projects:*" covers "projects:read")
        resource = scope.split(":")[0]
        if f"{resource}:*" in self.scopes:
            return True
        if "*" in self.scopes:  # Super admin scope
            return True
        return False

    def is_ip_allowed(self, ip_address: str) -> bool:
        """Check if IP address is allowed"""
        if not self.allowed_ips:
            return True  # No restrictions
        return ip_address in self.allowed_ips


# Available API Scopes
API_SCOPES = {
    # Projects
    "projects:read": "Read project data",
    "projects:write": "Create and update projects",
    "projects:delete": "Delete projects",
    # Simulations
    "simulations:read": "Read simulation results",
    "simulations:write": "Run simulations",
    # Offers
    "offers:read": "Read offers",
    "offers:write": "Create and update offers",
    "offers:sign": "Initiate e-signature process",
    # Components
    "components:read": "Read component database",
    "components:write": "Manage components",
    # Analytics
    "analytics:read": "Read analytics data",
    # Webhooks
    "webhooks:manage": "Manage webhook subscriptions",
    # Admin
    "admin:*": "Full administrative access",
}
