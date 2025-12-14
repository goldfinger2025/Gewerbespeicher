"""
User Model
SQLAlchemy ORM model for users table
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


# User roles within a tenant
class UserRole:
    OWNER = "owner"          # Full access, can manage tenant settings
    ADMIN = "admin"          # Can manage users and all projects
    MANAGER = "manager"      # Can manage projects and view analytics
    USER = "user"            # Can create and manage own projects
    VIEWER = "viewer"        # Read-only access


class User(Base):
    """User model for authentication and project ownership"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # tenant_id is nullable for backwards compatibility with existing users
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    company_name = Column(String(255))
    phone = Column(String(20))
    role = Column(String(50), default=UserRole.USER)  # Role within tenant
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)  # System-wide admin (super admin)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")

    @property
    def full_name(self) -> str:
        """Return user's full name"""
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    def has_role(self, *roles: str) -> bool:
        """Check if user has one of the specified roles"""
        return self.role in roles

    def can_manage_tenant(self) -> bool:
        """Check if user can manage tenant settings"""
        return self.role in [UserRole.OWNER] or self.is_admin

    def can_manage_users(self) -> bool:
        """Check if user can manage other users"""
        return self.role in [UserRole.OWNER, UserRole.ADMIN] or self.is_admin

    def can_manage_projects(self) -> bool:
        """Check if user can manage all projects"""
        return self.role in [UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER] or self.is_admin

    def can_view_analytics(self) -> bool:
        """Check if user can view analytics"""
        return self.role in [UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER] or self.is_admin

    def __repr__(self):
        return f"<User {self.email}>"
