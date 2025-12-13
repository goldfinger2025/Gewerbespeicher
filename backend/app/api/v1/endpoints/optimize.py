"""
Optimization Endpoints
KI-basierte Systemoptimierung
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.crud import project as project_crud
from app.crud import simulation as simulation_crud
from app.api.deps import get_current_user
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


# ============ ENDPOINTS ============

@router.post("/optimize", response_model=OptimizationResult)
async def optimize_system(
    request: OptimizationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    KI-basierte Systemoptimierung mit Claude

    Optimierungsziele:
    - max-roi: Maximale Rendite (schnellste Amortisation)
    - max-autonomy: Maximale Unabhängigkeit vom Netz
    - min-cost: Minimale Investitionskosten
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

    # Prepare project data for Claude
    project_data = {
        "customer_name": project.customer_name,
        "pv_peak_power_kw": project.pv_peak_power_kw,
        "battery_capacity_kwh": project.battery_capacity_kwh,
        "battery_power_kw": project.battery_power_kw,
        "annual_consumption_kwh": project.annual_consumption_kwh,
        "electricity_price_eur_kwh": project.electricity_price_eur_kwh,
    }

    # Get Claude service
    claude = get_claude_service()

    # Run optimization
    try:
        result = await claude.optimize_system(
            project=project_data,
            optimization_target=request.optimization_target
        )

        return OptimizationResult(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimierung fehlgeschlagen: {str(e)}"
        )


@router.post("/recommend-components", response_model=List[ComponentRecommendation])
async def recommend_components(
    project_id: str,
    budget_eur: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    KI-basierte Komponentenempfehlungen

    Gibt passende Wechselrichter, Speicher und Module zurück.
    """
    # Validate project_id
    try:
        project_uuid = UUID(project_id)
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

    # Prepare project data for Claude
    project_data = {
        "pv_peak_power_kw": project.pv_peak_power_kw,
        "battery_capacity_kwh": project.battery_capacity_kwh,
        "battery_power_kw": project.battery_power_kw,
        "annual_consumption_kwh": project.annual_consumption_kwh,
    }

    # Get Claude service
    claude = get_claude_service()

    try:
        recommendations = await claude.get_component_recommendations(
            project=project_data,
            budget_eur=budget_eur
        )

        return [ComponentRecommendation(**r) for r in recommendations]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Empfehlung fehlgeschlagen: {str(e)}"
        )


@router.get("/faq/{project_id}")
async def get_project_faq(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generiert kundenspezifische FAQ für ein Projekt
    """
    # Validate project_id
    try:
        project_uuid = UUID(project_id)
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

    # Get latest simulation
    simulation = await simulation_crud.get_latest_simulation(db=db, project_id=project_uuid)

    # Prepare data for Claude
    project_data = {
        "customer_name": project.customer_name,
        "pv_peak_power_kw": project.pv_peak_power_kw,
        "battery_capacity_kwh": project.battery_capacity_kwh,
        "annual_consumption_kwh": project.annual_consumption_kwh,
    }

    simulation_data = {}
    if simulation and simulation.status == "completed":
        simulation_data = {
            "pv_generation_kwh": simulation.pv_generation_kwh,
            "autonomy_degree_percent": simulation.autonomy_degree_percent,
            "annual_savings_eur": simulation.annual_savings_eur,
            "payback_period_years": simulation.payback_period_years,
        }

    # Get Claude service
    claude = get_claude_service()

    try:
        faq = await claude.generate_customer_faq(
            project=project_data,
            simulation=simulation_data
        )

        return {"faq": faq}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"FAQ-Generierung fehlgeschlagen: {str(e)}"
        )
