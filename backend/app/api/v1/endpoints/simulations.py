"""
Simulation Endpoints
PV + Storage System Simulation
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.simulation import Simulation
from app.crud import project as project_crud
from app.crud import simulation as simulation_crud
from app.api.deps import get_current_user
from app.core.simulator import PVStorageSimulator


router = APIRouter()


# ============ PYDANTIC MODELS ============

class SimulationRequest(BaseModel):
    project_id: str
    simulation_type: Optional[str] = "standard"  # standard, peak-shaving, arbitrage


class SimulationKPIs(BaseModel):
    pv_generation_kwh: float
    self_consumption_kwh: float
    grid_import_kwh: float
    grid_export_kwh: float
    autonomy_degree_percent: float
    self_consumption_ratio_percent: float
    annual_savings_eur: float
    payback_period_years: float
    battery_cycles: float


class MonthlyData(BaseModel):
    month: int
    pv_generation_kwh: float
    consumption_kwh: float
    self_consumption_kwh: float
    grid_import_kwh: float
    grid_export_kwh: float


class SimulationResponse(BaseModel):
    id: str
    project_id: str
    simulation_type: str
    status: str  # pending, running, completed, failed
    results: Optional[SimulationKPIs] = None
    monthly_summary: Optional[List[MonthlyData]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ HELPER FUNCTIONS ============

def simulation_to_response(simulation: Simulation) -> SimulationResponse:
    """Convert SQLAlchemy Simulation model to Pydantic response"""
    results = None
    if simulation.status == "completed" and simulation.pv_generation_kwh is not None:
        results = SimulationKPIs(
            pv_generation_kwh=simulation.pv_generation_kwh or 0,
            self_consumption_kwh=simulation.self_consumed_kwh or 0,
            grid_import_kwh=simulation.consumed_from_grid_kwh or 0,
            grid_export_kwh=simulation.fed_to_grid_kwh or 0,
            autonomy_degree_percent=simulation.autonomy_degree_percent or 0,
            self_consumption_ratio_percent=simulation.self_consumption_ratio_percent or 0,
            annual_savings_eur=simulation.annual_savings_eur or 0,
            payback_period_years=simulation.payback_period_years or 0,
            battery_cycles=simulation.battery_discharge_cycles or 0,
        )

    monthly_summary = None
    if simulation.monthly_summary:
        monthly_summary = [MonthlyData(**m) for m in simulation.monthly_summary]

    return SimulationResponse(
        id=str(simulation.id),
        project_id=str(simulation.project_id),
        simulation_type=simulation.simulation_type,
        status=simulation.status,
        results=results,
        monthly_summary=monthly_summary,
        created_at=simulation.created_at,
    )


# ============ ENDPOINTS ============

@router.post("", response_model=SimulationResponse, status_code=status.HTTP_201_CREATED)
async def run_simulation(
    request: SimulationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Run a new simulation for a project
    """
    # Validate project_id
    try:
        project_uuid = UUID(request.project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Projekt-ID"
        )

    # Get project and verify ownership
    project = await project_crud.get_project_by_id(
        db=db,
        project_id=project_uuid,
        user_id=current_user.id
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projekt nicht gefunden"
        )

    # Create simulation record
    simulation = await simulation_crud.create_simulation(
        db=db,
        project_id=project.id,
        simulation_type=request.simulation_type,
    )

    # Initialize simulator
    simulator = PVStorageSimulator(
        latitude=project.latitude or 54.5,
        longitude=project.longitude or 9.3
    )

    # Run simulation
    try:
        results = await simulator.simulate_year(
            pv_peak_kw=project.pv_peak_power_kw,
            battery_kwh=project.battery_capacity_kwh,
            battery_power_kw=project.battery_power_kw or (project.battery_capacity_kwh * 0.5),
            annual_consumption_kwh=project.annual_consumption_kwh,
            electricity_price=project.electricity_price_eur_kwh or 0.30,
            feed_in_tariff=project.feed_in_tariff_eur_kwh or 0.08,
            pv_tilt=project.pv_tilt_angle or 30.0
        )

        # Calculate self-consumption ratio
        self_consumption_ratio = 0
        if results["pv_generation_kwh"] > 0:
            self_consumption_ratio = (results["self_consumption_kwh"] / results["pv_generation_kwh"]) * 100

        # Generate monthly summary from results
        monthly_summary = results.get("monthly_summary", [])

        # Update simulation with results
        simulation = await simulation_crud.complete_simulation(
            db=db,
            simulation=simulation,
            pv_generation_kwh=results["pv_generation_kwh"],
            self_consumed_kwh=results["self_consumption_kwh"],
            consumed_from_grid_kwh=results["grid_import_kwh"],
            fed_to_grid_kwh=results["grid_export_kwh"],
            autonomy_degree_percent=results["autonomy_degree_percent"],
            self_consumption_ratio_percent=self_consumption_ratio,
            annual_savings_eur=results["annual_savings_eur"],
            payback_period_years=results["payback_period_years"],
            battery_discharge_cycles=results["battery_cycles"],
            monthly_summary=monthly_summary if monthly_summary else None,
        )

        return simulation_to_response(simulation)

    except Exception as e:
        # Mark simulation as failed
        await simulation_crud.fail_simulation(db=db, simulation=simulation)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation fehlgeschlagen: {str(e)}"
        )


@router.get("/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(
    simulation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get simulation results by ID
    """
    try:
        uuid_id = UUID(simulation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Simulations-ID"
        )

    simulation = await simulation_crud.get_simulation_by_id(db=db, simulation_id=uuid_id)

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation nicht gefunden"
        )

    # Verify user owns the project
    project = await project_crud.get_project_by_id(
        db=db,
        project_id=simulation.project_id,
        user_id=current_user.id
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation nicht gefunden"
        )

    return simulation_to_response(simulation)


@router.get("/project/{project_id}", response_model=List[SimulationResponse])
async def get_project_simulations(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all simulations for a project
    """
    try:
        uuid_id = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Projekt-ID"
        )

    # Verify user owns the project
    project = await project_crud.get_project_by_id(
        db=db,
        project_id=uuid_id,
        user_id=current_user.id
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projekt nicht gefunden"
        )

    simulations = await simulation_crud.get_simulations_by_project(db=db, project_id=uuid_id)

    return [simulation_to_response(s) for s in simulations]


@router.get("/project/{project_id}/latest", response_model=SimulationResponse)
async def get_latest_project_simulation(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the latest simulation for a project
    """
    try:
        uuid_id = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Projekt-ID"
        )

    # Verify user owns the project
    project = await project_crud.get_project_by_id(
        db=db,
        project_id=uuid_id,
        user_id=current_user.id
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projekt nicht gefunden"
        )

    simulation = await simulation_crud.get_latest_simulation(db=db, project_id=uuid_id)

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keine Simulation für dieses Projekt gefunden"
        )

    return simulation_to_response(simulation)
