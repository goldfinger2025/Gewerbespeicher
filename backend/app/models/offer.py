"""
Offer Model
SQLAlchemy ORM model for quotes/offers
"""

from sqlalchemy import Column, String, Boolean, DateTime, Date, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Offer(Base):
    """Offer model for storing generated quotes"""

    __tablename__ = "offers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    # Offer Metadata
    offer_number = Column(String(50), unique=True)
    offer_date = Column(DateTime, server_default=func.now())
    valid_until = Column(Date)

    # Content
    offer_text = Column(Text)
    technical_specs = Column(JSONB)
    components_bom = Column(JSONB)  # Bill of Materials
    pricing_breakdown = Column(JSONB)

    # Professional Offer Details (für vollständige Angebote)
    warranty_info = Column(JSONB)  # Garantieinformationen
    subsidy_info = Column(JSONB)  # Förderinformationen (KfW, Länder)
    payment_terms = Column(Text)  # Zahlungsbedingungen
    terms_reference = Column(String(255))  # AGB-Verweis
    service_package = Column(JSONB)  # Wartungs-/Service-Pakete

    # E-Signature
    signature_link = Column(String(500))
    is_signed = Column(Boolean, default=False)
    signed_at = Column(DateTime)
    signer_name = Column(String(255))

    # PDF
    pdf_path = Column(String(500))
    pdf_generated_at = Column(DateTime)

    # CRM Integration
    hubspot_deal_id = Column(String(100))
    crm_sync_status = Column(String(50), default="pending")

    # Status
    status = Column(String(50), default="draft", index=True)  # draft, sent, viewed, signed, completed, rejected

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    simulation = relationship("Simulation", back_populates="offers")
    project = relationship("Project", back_populates="offers")

    def __repr__(self):
        return f"<Offer {self.offer_number}>"
