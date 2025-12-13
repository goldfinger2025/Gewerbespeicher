"""
Audit Log Model
SQLAlchemy ORM model for tracking changes
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.database import Base


class AuditLog(Base):
    """Audit log model for tracking entity changes"""

    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    entity_type = Column(String(50), index=True)  # project, simulation, offer, etc.
    entity_id = Column(UUID(as_uuid=True), index=True)
    action = Column(String(50))  # create, update, delete
    changes = Column(JSONB)  # What was changed
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.entity_type} {self.entity_id}>"
