"""
Simulation Endpoints
PV + Storage System Simulation
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import uuid4

from app.core.simulator import PVStorageSimulator

router = APIRouter()


# ============ PYDANTIC MODELS ============

class SimulationRequest(BaseModel):
    project_id: str
    simulation_type: Optional[str] = "standard"  # standard, peak-shaving, arbitrage
    run_async: Optional[bool] = False


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


class SimulationResponse(BaseModel):
    id: str
    project_id: str
    simulation_type: str
    status: str  # pending, running, completed, failed
    results: Optional[SimulationKPIs] = None
    created_at: datetime


# ============ IN-MEMORY STORAGE (MVP) ============

_simulations_db: dict = {}

# Import projects storage (for lookups)
from app.api.v1.endpoints.projects import _projects_db


# ============ ENDPOINTS ============

@router.post("", response_model=SimulationResponse, status_code=201)
async def run_simulation(request: SimulationRequest):
    """
    Run a new simulation for a project
    """
    # Get project data
    if request.project_id not in _projects_db:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    
    project = _projects_db[request.project_id]
    
    # Initialize simulator
    simulator = PVStorageSimulator(
        latitude=project.get("latitude", 54.5),
        longitude=project.get("longitude", 9.3)
    )
    
    # Run simulation
    try:
        results = await simulator.simulate_year(
            pv_peak_kw=project["pv_peak_power_kw"],
            battery_kwh=project["battery_capacity_kwh"],
            battery_power_kw=project.get("battery_power_kw", project["battery_capacity_kwh"] * 0.5),
            annual_consumption_kwh=project["annual_consumption_kwh"],
            electricity_price=project.get("electricity_price_eur_kwh", 0.30),
            feed_in_tariff=0.08,
            pv_tilt=project.get("pv_tilt_angle", 30.0)
        )
        
        simulation_id = str(uuid4())
        now = datetime.utcnow()
        
        # Calculate self-consumption ratio
        self_consumption_ratio = 0
        if results["pv_generation_kwh"] > 0:
            self_consumption_ratio = (results["self_consumption_kwh"] / results["pv_generation_kwh"]) * 100
        
        simulation = {
            "id": simulation_id,
            "project_id": request.project_id,
            "simulation_type": request.simulation_type,
            "status": "completed",
            "results": SimulationKPIs(
                **results,
                self_consumption_ratio_percent=self_consumption_ratio
            ),
            "created_at": now
        }
        
        _simulations_db[simulation_id] = simulation
        
        return SimulationResponse(**simulation)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Simulation fehlgeschlagen: {str(e)}"
        )


@router.get("/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(simulation_id: str):
    """
    Get simulation results by ID
    """
    if simulation_id not in _simulations_db:
        raise HTTPException(status_code=404, detail="Simulation nicht gefunden")
    
    return SimulationResponse(**_simulations_db[simulation_id])


@router.get("/project/{project_id}", response_model=List[SimulationResponse])
async def get_project_simulations(project_id: str):
    """
    Get all simulations for a project
    """
    simulations = [
        SimulationResponse(**s)
        for s in _simulations_db.values()
        if s["project_id"] == project_id
    ]
    
    # Sort by created_at descending
    simulations.sort(key=lambda x: x.created_at, reverse=True)
    
    return simulations
