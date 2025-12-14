"""
Tenant Model
SQLAlchemy ORM model for multi-tenant support
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Float, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Tenant(Base):
    """Tenant model for multi-tenant/white-label support"""

    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic Info
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)  # URL-friendly identifier
    description = Column(Text)

    # Contact Info
    company_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20))
    address = Column(String(500))
    postal_code = Column(String(10))
    city = Column(String(100))
    country = Column(String(100), default="Deutschland")

    # White-Label Branding
    logo_url = Column(String(500))
    favicon_url = Column(String(500))
    primary_color = Column(String(7), default="#2563eb")  # Blue
    secondary_color = Column(String(7), default="#10b981")  # Green
    accent_color = Column(String(7), default="#f59e0b")  # Orange
    font_family = Column(String(100), default="Inter")

    # Custom Domain
    custom_domain = Column(String(255), unique=True)  # e.g., planner.partnerfirma.de

    # Feature Flags
    features = Column(JSONB, default=dict)  # {"pdf_export": true, "crm_sync": true, ...}

    # Limits
    max_users = Column(Float, default=10)
    max_projects = Column(Float, default=100)
    max_storage_mb = Column(Float, default=1000)

    # Subscription / Billing
    subscription_plan = Column(String(50), default="starter")  # starter, professional, enterprise
    subscription_status = Column(String(50), default="active")  # active, trial, suspended, cancelled
    trial_ends_at = Column(DateTime)

    # API Access
    api_enabled = Column(Boolean, default=False)
    api_rate_limit = Column(Float, default=100)  # requests per minute

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant {self.name} ({self.slug})>"

    @property
    def branding(self) -> dict:
        """Return branding configuration"""
        return {
            "logo_url": self.logo_url,
            "favicon_url": self.favicon_url,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "accent_color": self.accent_color,
            "font_family": self.font_family,
            "company_name": self.company_name,
        }

    def has_feature(self, feature_name: str) -> bool:
        """Check if tenant has a specific feature enabled"""
        if not self.features:
            return False
        return self.features.get(feature_name, False)

    def get_limits(self) -> dict:
        """Return tenant limits"""
        return {
            "max_users": self.max_users,
            "max_projects": self.max_projects,
            "max_storage_mb": self.max_storage_mb,
            "api_rate_limit": self.api_rate_limit,
        }
