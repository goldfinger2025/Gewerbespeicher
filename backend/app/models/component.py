"""
Component Model
SQLAlchemy ORM model for PV/Battery/Inverter component catalog
"""

from sqlalchemy import Column, String, Boolean, DateTime, Float, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.database import Base


class Component(Base):
    """Component model for product catalog (batteries, inverters, PV modules)"""

    __tablename__ = "components"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Classification
    category = Column(String(50), nullable=False, index=True)  # battery, inverter, pv_module
    subcategory = Column(String(50))

    # Product Info
    manufacturer = Column(String(100), nullable=False, index=True)
    model = Column(String(150), nullable=False)
    description = Column(Text)
    specification = Column(JSONB)  # Technical specs as JSON

    # Pricing
    unit_price_eur = Column(Float)
    supplier_sku = Column(String(100))
    availability_status = Column(String(50))  # in_stock, out_of_stock, on_order

    # Compatibility
    compatible_with = Column(JSONB)  # List of compatible component IDs/models

    # Admin
    is_active = Column(Boolean, default=True)
    data_source = Column(String(100))
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Component {self.manufacturer} {self.model}>"
