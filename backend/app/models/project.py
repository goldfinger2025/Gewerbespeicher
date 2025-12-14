"""
Project Model
SQLAlchemy ORM model for PV+Storage projects
"""

from sqlalchemy import Column, String, DateTime, Float, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Project(Base):
    """Project model for PV+Storage system configurations"""

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Customer Info
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255))
    customer_phone = Column(String(20))
    customer_company = Column(String(255))

    # Location
    address = Column(String(500), nullable=False)
    postal_code = Column(String(10), index=True)
    city = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)

    # Project Data
    project_name = Column(String(255))
    description = Column(Text)
    status = Column(String(50), default="draft", index=True)  # draft, active, completed, archived

    # PV System
    pv_peak_power_kw = Column(Float)
    pv_orientation = Column(String(50))
    pv_tilt_angle = Column(Float)
    roof_area_sqm = Column(Float)

    # Battery System
    battery_capacity_kwh = Column(Float)
    battery_power_kw = Column(Float)
    battery_chemistry = Column(String(50))
    battery_manufacturer = Column(String(100))

    # Consumption
    annual_consumption_kwh = Column(Float)
    peak_load_kw = Column(Float)
    load_profile_type = Column(String(50), default="office")  # office, retail, production, warehouse

    # Cost Parameters
    electricity_price_eur_kwh = Column(Float)
    grid_fee_eur_kwh = Column(Float)
    feed_in_tariff_eur_kwh = Column(Float)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="projects")
    simulations = relationship("Simulation", back_populates="project", cascade="all, delete-orphan")
    offers = relationship("Offer", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project {self.project_name or self.customer_name}>"
