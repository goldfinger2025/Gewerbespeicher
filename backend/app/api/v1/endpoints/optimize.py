"""
Optimization Endpoints
KI-basierte Systemoptimierung
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.services.claude_service import get_claude_service

router = APIRouter()


# ============ PYDANTIC MODELS ============

class OptimizationRequest(BaseModel):
    project_id: str
    optimization_target: str = "max-roi"  # max-roi, max-autonomy, min-cost
    constraints: Optional[dict] = None


class OptimizationResult(BaseModel):
    optimized_pv_kw: float
    optimized_battery_kwh: float
    optimized_battery_power_kw: float
    expected_autonomy_percent: float
    expected_savings_eur: float
    expected_payback_years: float
    investment_delta_eur: float
    recommendations: List[str]
    reasoning: str


class ComponentRecommendation(BaseModel):
    category: str
    manufacturer: str
    model: str
    quantity: int
    unit_price_eur: float
    reason: str


# Import projects storage
from app.api.v1.endpoints.projects import _projects_db


# ============ ENDPOINTS ============

@router.post("/optimize", response_model=OptimizationResult)
async def optimize_system(request: OptimizationRequest):
    """
    KI-basierte Systemoptimierung mit Claude
    
    Optimierungsziele:
    - max-roi: Maximale Rendite (schnellste Amortisation)
    - max-autonomy: Maximale Unabhängigkeit vom Netz
    - min-cost: Minimale Investitionskosten
    """
    # Get project
    if request.project_id not in _projects_db:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    
    project = _projects_db[request.project_id]
    
    # Get Claude service
    claude = get_claude_service()
    
    # Run optimization
    try:
        result = await claude.optimize_system(
            project=project,
            optimization_target=request.optimization_target
        )
        
        return OptimizationResult(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Optimierung fehlgeschlagen: {str(e)}"
        )


@router.post("/recommend-components", response_model=List[ComponentRecommendation])
async def recommend_components(
    project_id: str,
    budget_eur: Optional[float] = None
):
    """
    KI-basierte Komponentenempfehlungen
    
    Gibt passende Wechselrichter, Speicher und Module zurück.
    """
    # Get project
    if project_id not in _projects_db:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    
    project = _projects_db[project_id]
    
    # Get Claude service
    claude = get_claude_service()
    
    try:
        recommendations = await claude.get_component_recommendations(
            project=project,
            budget_eur=budget_eur
        )
        
        return [ComponentRecommendation(**r) for r in recommendations]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Empfehlung fehlgeschlagen: {str(e)}"
        )


@router.get("/faq/{project_id}")
async def get_project_faq(project_id: str):
    """
    Generiert kundenspezifische FAQ für ein Projekt
    """
    if project_id not in _projects_db:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    
    project = _projects_db[project_id]
    
    # Get simulation if available
    from app.api.v1.endpoints.simulations import _simulations_db
    
    simulation = {}
    for sim in _simulations_db.values():
        if sim.get("project_id") == project_id:
            results = sim.get("results", {})
            if hasattr(results, "model_dump"):
                simulation = results.model_dump()
            else:
                simulation = results
            break
    
    # Get Claude service
    claude = get_claude_service()
    
    try:
        faq = await claude.generate_customer_faq(
            project=project,
            simulation=simulation
        )
        
        return {"faq": faq}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"FAQ-Generierung fehlgeschlagen: {str(e)}"
        )
