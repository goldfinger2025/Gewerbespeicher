"""
Simulation CRUD Operations
Database operations for simulations
"""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID

from app.models.simulation import Simulation


async def get_simulation_by_id(
    db: AsyncSession,
    simulation_id: UUID
) -> Optional[Simulation]:
    """Get a simulation by ID"""
    result = await db.execute(select(Simulation).where(Simulation.id == simulation_id))
    return result.scalar_one_or_none()


async def get_simulations_by_project(
    db: AsyncSession,
    project_id: UUID
) -> List[Simulation]:
    """Get all simulations for a project"""
    result = await db.execute(
        select(Simulation)
        .where(Simulation.project_id == project_id)
        .order_by(Simulation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_latest_simulation(
    db: AsyncSession,
    project_id: UUID
) -> Optional[Simulation]:
    """Get the latest simulation for a project"""
    result = await db.execute(
        select(Simulation)
        .where(Simulation.project_id == project_id)
        .where(Simulation.is_latest.is_(True))
        .order_by(Simulation.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_simulation(
    db: AsyncSession,
    project_id: UUID,
    simulation_type: str = "standard",
    **kwargs
) -> Simulation:
    """Create a new simulation"""
    # Mark previous simulations as not latest
    await db.execute(
        update(Simulation)
        .where(Simulation.project_id == project_id)
        .where(Simulation.is_latest.is_(True))
        .values(is_latest=False)
    )

    simulation = Simulation(
        project_id=project_id,
        simulation_type=simulation_type,
        is_latest=True,
        status="pending",
        **kwargs
    )
    db.add(simulation)
    await db.flush()
    await db.refresh(simulation)
    return simulation


async def update_simulation(
    db: AsyncSession,
    simulation: Simulation,
    **kwargs
) -> Simulation:
    """Update simulation fields"""
    for key, value in kwargs.items():
        if hasattr(simulation, key) and value is not None:
            setattr(simulation, key, value)
    await db.flush()
    await db.refresh(simulation)
    return simulation


async def complete_simulation(
    db: AsyncSession,
    simulation: Simulation,
    pv_generation_kwh: float,
    self_consumed_kwh: float,
    consumed_from_grid_kwh: float,
    fed_to_grid_kwh: float,
    autonomy_degree_percent: float,
    self_consumption_ratio_percent: float,
    annual_savings_eur: float,
    payback_period_years: float,
    battery_discharge_cycles: float,
    monthly_summary: Optional[dict] = None,
    hourly_data: Optional[dict] = None,
) -> Simulation:
    """Update simulation with results and mark as completed"""
    simulation.status = "completed"
    simulation.pv_generation_kwh = pv_generation_kwh
    simulation.self_consumed_kwh = self_consumed_kwh
    simulation.consumed_from_grid_kwh = consumed_from_grid_kwh
    simulation.fed_to_grid_kwh = fed_to_grid_kwh
    simulation.autonomy_degree_percent = autonomy_degree_percent
    simulation.self_consumption_ratio_percent = self_consumption_ratio_percent
    simulation.annual_savings_eur = annual_savings_eur
    simulation.payback_period_years = payback_period_years
    simulation.battery_discharge_cycles = battery_discharge_cycles
    simulation.monthly_summary = monthly_summary
    simulation.hourly_data = hourly_data

    await db.flush()
    await db.refresh(simulation)
    return simulation


async def fail_simulation(
    db: AsyncSession,
    simulation: Simulation,
    error_message: Optional[str] = None
) -> Simulation:
    """Mark simulation as failed"""
    simulation.status = "failed"
    await db.flush()
    await db.refresh(simulation)
    return simulation


async def delete_simulation(db: AsyncSession, simulation: Simulation) -> None:
    """Delete a simulation"""
    await db.delete(simulation)
    await db.flush()
