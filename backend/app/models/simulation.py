"""
Simulation Model
SQLAlchemy ORM model for PV+Storage simulation results
"""

from sqlalchemy import Column, String, Boolean, DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Simulation(Base):
    """Simulation model for storing PV+Storage simulation results"""

    __tablename__ = "simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # Parameters
    simulation_type = Column(String(50), default="standard")  # standard, peak-shaving, arbitrage
    time_resolution = Column(String(20), default="hourly")

    # Annual Results
    pv_generation_kwh = Column(Float)
    consumed_from_grid_kwh = Column(Float)
    self_consumed_kwh = Column(Float)
    fed_to_grid_kwh = Column(Float)
    battery_discharge_cycles = Column(Float)

    # Key Metrics
    autonomy_degree_percent = Column(Float)
    self_consumption_ratio_percent = Column(Float)
    pv_coverage_percent = Column(Float)

    # Financial Results
    annual_savings_eur = Column(Float)
    total_savings_eur = Column(Float)
    payback_period_years = Column(Float)
    npv_eur = Column(Float)
    irr_percent = Column(Float)

    # Detailed Data (JSON)
    hourly_data = Column(JSONB)
    monthly_summary = Column(JSONB)

    # Status
    is_latest = Column(Boolean, default=True, index=True)
    status = Column(String(50), default="completed")  # pending, running, completed, failed

    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    project = relationship("Project", back_populates="simulations")
    offers = relationship("Offer", back_populates="simulation")

    def __repr__(self):
        return f"<Simulation {self.id} for Project {self.project_id}>"
