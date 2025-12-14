"""
Optimization Endpoints
KI-basierte Systemoptimierung mit Claude

Phase 2 Features:
- Intelligente System-Dimensionierung basierend auf Lastprofil
- Vergleichsszenarien für verschiedene Konfigurationen
- Erweiterte Angebotstexte
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
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


# New Phase 2 Models
class DimensioningConstraints(BaseModel):
    max_budget: Optional[float] = Field(None, description="Maximum budget in EUR")
    max_roof_area: Optional[float] = Field(None, description="Maximum roof area in m²")
    min_autonomy: Optional[float] = Field(None, description="Minimum autonomy percentage")


class DimensioningRequest(BaseModel):
    project_id: str
    constraints: Optional[DimensioningConstraints] = None


class ExpectedResults(BaseModel):
    autonomy_percent: float
    self_consumption_percent: float
    annual_savings_eur: float
    payback_years: float
    co2_savings_tons: float


class Investment(BaseModel):
    pv_cost_eur: float
    battery_cost_eur: float
    installation_cost_eur: float
    total_cost_eur: float


class DimensioningFactors(BaseModel):
    pv_to_consumption_ratio: float
    battery_to_pv_ratio: float
    specific_yield_kwh_per_kwp: int


class DimensioningResult(BaseModel):
    recommended_pv_kw: float
    recommended_battery_kwh: float
    recommended_battery_power_kw: float
    expected_results: ExpectedResults
    investment: Investment
    dimensioning_factors: DimensioningFactors
    reasoning: str
    recommendations: List[str]


class ScenarioData(BaseModel):
    name: str
    description: str
    pv_kw: float
    battery_kwh: float
    investment_eur: float
    autonomy_percent: float
    annual_savings_eur: float
    payback_years: float
    npv_20y_eur: float
    co2_savings_tons: float
    highlight: str


class ComparisonResult(BaseModel):
    scenarios: List[ScenarioData]
    recommendation: str
    comparison_summary: str


class DetailedOfferText(BaseModel):
    greeting: str
    executive_summary: str
    system_description: str
    economic_benefits: str
    environmental_benefits: str
    next_steps: str
    closing: str


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


# ============ PHASE 2 ENDPOINTS ============

@router.post("/dimension", response_model=DimensioningResult)
async def dimension_system(
    request: DimensioningRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    KI-basierte System-Dimensionierung basierend auf Lastprofil

    Berechnet optimale PV- und Speichergröße unter Berücksichtigung von:
    - Lastprofil-Typ (Büro, Einzelhandel, Produktion, Lager)
    - Jahresverbrauch und Spitzenlast
    - Optionale Constraints (Budget, Dachfläche, Min-Autarkie)
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

    # Prepare project data
    project_data = {
        "customer_name": project.customer_name,
        "load_profile_type": project.load_profile_type or "office",
        "annual_consumption_kwh": project.annual_consumption_kwh,
        "peak_load_kw": project.peak_load_kw,
        "electricity_price_eur_kwh": project.electricity_price_eur_kwh,
        "feed_in_tariff_eur_kwh": project.feed_in_tariff_eur_kwh or 0.08,
        "city": project.city,
        "latitude": project.latitude,
        "longitude": project.longitude,
        "roof_area_sqm": project.roof_area_sqm,
    }

    # Prepare constraints
    constraints = None
    if request.constraints:
        constraints = request.constraints.model_dump(exclude_none=True)

    # Get Claude service
    claude = get_claude_service()

    try:
        result = await claude.dimension_system(
            project=project_data,
            constraints=constraints
        )

        return DimensioningResult(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dimensionierung fehlgeschlagen: {str(e)}"
        )


@router.get("/compare/{project_id}", response_model=ComparisonResult)
async def compare_scenarios(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generiert Vergleichsszenarien für ein Projekt

    Erstellt 3 Szenarien:
    1. Basis - Aktuelle Konfiguration
    2. ROI-Optimiert - Schnellste Amortisation
    3. Autarkie-Optimiert - Maximale Unabhängigkeit
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

    if not simulation or simulation.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keine abgeschlossene Simulation vorhanden. Bitte zuerst simulieren."
        )

    # Prepare data
    project_data = {
        "pv_peak_power_kw": project.pv_peak_power_kw,
        "battery_capacity_kwh": project.battery_capacity_kwh,
        "annual_consumption_kwh": project.annual_consumption_kwh,
        "electricity_price_eur_kwh": project.electricity_price_eur_kwh,
    }

    simulation_data = {
        "pv_generation_kwh": simulation.pv_generation_kwh,
        "autonomy_degree_percent": simulation.autonomy_degree_percent,
        "annual_savings_eur": simulation.annual_savings_eur,
        "payback_period_years": simulation.payback_period_years,
    }

    # Get Claude service
    claude = get_claude_service()

    try:
        result = await claude.generate_comparison_scenarios(
            project=project_data,
            simulation=simulation_data
        )

        return ComparisonResult(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Szenarien-Vergleich fehlgeschlagen: {str(e)}"
        )


@router.get("/offer-text/{project_id}", response_model=DetailedOfferText)
async def get_detailed_offer_text(
    project_id: str,
    include_monthly: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generiert detaillierten, modularen Angebotstext

    Gibt separate Textabschnitte zurück für flexible Verwendung:
    - greeting: Persönliche Anrede
    - executive_summary: Management Summary
    - system_description: Technische Beschreibung
    - economic_benefits: Wirtschaftliche Vorteile
    - environmental_benefits: Umweltvorteile
    - next_steps: Call-to-Action
    - closing: Abschluss
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

    if not simulation or simulation.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keine abgeschlossene Simulation vorhanden."
        )

    # Prepare data
    project_data = {
        "customer_name": project.customer_name,
        "customer_company": project.customer_company,
        "address": project.address,
        "postal_code": project.postal_code,
        "city": project.city,
        "pv_peak_power_kw": project.pv_peak_power_kw,
        "battery_capacity_kwh": project.battery_capacity_kwh,
        "battery_power_kw": project.battery_power_kw,
        "annual_consumption_kwh": project.annual_consumption_kwh,
    }

    simulation_data = {
        "pv_generation_kwh": simulation.pv_generation_kwh,
        "self_consumption_kwh": simulation.self_consumption_kwh,
        "autonomy_degree_percent": simulation.autonomy_degree_percent,
        "self_consumption_ratio_percent": simulation.self_consumption_ratio_percent,
        "annual_savings_eur": simulation.annual_savings_eur,
        "payback_period_years": simulation.payback_period_years,
        "monthly_summary": simulation.monthly_summary,
    }

    # Get Claude service
    claude = get_claude_service()

    try:
        result = await claude.generate_detailed_offer_text(
            project=project_data,
            simulation=simulation_data,
            include_monthly=include_monthly
        )

        return DetailedOfferText(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Angebotstext-Generierung fehlgeschlagen: {str(e)}"
        )
