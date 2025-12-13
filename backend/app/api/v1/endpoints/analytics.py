"""
Analytics Endpoints
Dashboard-Metriken und Portfolio-Übersicht
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.simulation import Simulation
from app.models.offer import Offer
from app.api.deps import get_current_user


router = APIRouter()


# ============ PYDANTIC MODELS ============

class PortfolioMetrics(BaseModel):
    total_projects: int
    active_projects: int
    completed_projects: int
    draft_projects: int
    total_pv_capacity_kw: float
    total_battery_capacity_kwh: float
    total_annual_consumption_kwh: float
    avg_autonomy_percent: Optional[float]
    total_annual_savings_eur: Optional[float]
    total_investment_eur: Optional[float]
    avg_payback_years: Optional[float]


class ProjectSummary(BaseModel):
    id: str
    customer_name: str
    project_name: Optional[str]
    pv_kw: float
    battery_kwh: float
    status: str
    autonomy_percent: Optional[float]
    annual_savings_eur: Optional[float]
    created_at: datetime


class MonthlyTrend(BaseModel):
    month: str
    projects_created: int
    total_pv_kw: float
    total_battery_kwh: float


class DashboardResponse(BaseModel):
    metrics: PortfolioMetrics
    recent_projects: List[ProjectSummary]
    monthly_trends: List[MonthlyTrend]
    offers_pending: int
    offers_signed: int


# ============ ENDPOINTS ============

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard_metrics(
    period: Optional[str] = "month",  # week, month, year
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Dashboard-Metriken für den aktuellen Benutzer

    Gibt Portfolio-Übersicht, Trends und KPIs zurück.
    """
    # Calculate date range based on period (reserved for future filtering)
    now = datetime.utcnow()
    if period == "week":
        _start_date = now - timedelta(days=7)
    elif period == "year":
        _start_date = now - timedelta(days=365)
    else:  # month (default)
        _start_date = now - timedelta(days=30)

    # TODO: Use _start_date for filtering projects by date range

    # Get all user's projects
    projects_query = select(Project).where(
        Project.user_id == current_user.id
    )
    result = await db.execute(projects_query)
    projects = result.scalars().all()

    # Calculate portfolio metrics
    total_projects = len(projects)
    active_projects = sum(1 for p in projects if p.status == "active")
    completed_projects = sum(1 for p in projects if p.status == "completed")
    draft_projects = sum(1 for p in projects if p.status == "draft")

    total_pv = sum(p.pv_peak_power_kw or 0 for p in projects)
    total_battery = sum(p.battery_capacity_kwh or 0 for p in projects)
    total_consumption = sum(p.annual_consumption_kwh or 0 for p in projects)

    # Get simulations for metrics
    simulation_metrics = await _get_simulation_metrics(db, current_user.id)

    metrics = PortfolioMetrics(
        total_projects=total_projects,
        active_projects=active_projects,
        completed_projects=completed_projects,
        draft_projects=draft_projects,
        total_pv_capacity_kw=total_pv,
        total_battery_capacity_kwh=total_battery,
        total_annual_consumption_kwh=total_consumption,
        avg_autonomy_percent=simulation_metrics.get("avg_autonomy"),
        total_annual_savings_eur=simulation_metrics.get("total_savings"),
        total_investment_eur=simulation_metrics.get("total_investment"),
        avg_payback_years=simulation_metrics.get("avg_payback"),
    )

    # Get recent projects with simulation data
    recent_projects = await _get_recent_projects(db, current_user.id, limit=5)

    # Get monthly trends
    monthly_trends = await _get_monthly_trends(db, current_user.id, months=6)

    # Get offer counts
    offer_counts = await _get_offer_counts(db, current_user.id)

    return DashboardResponse(
        metrics=metrics,
        recent_projects=recent_projects,
        monthly_trends=monthly_trends,
        offers_pending=offer_counts.get("pending", 0),
        offers_signed=offer_counts.get("signed", 0),
    )


@router.get("/portfolio-summary")
async def get_portfolio_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Kompakte Portfolio-Zusammenfassung für Widgets
    """
    # Get aggregated metrics
    query = select(
        func.count(Project.id).label("project_count"),
        func.sum(Project.pv_peak_power_kw).label("total_pv"),
        func.sum(Project.battery_capacity_kwh).label("total_battery"),
        func.sum(Project.annual_consumption_kwh).label("total_consumption"),
    ).where(Project.user_id == current_user.id)

    result = await db.execute(query)
    row = result.one()

    return {
        "project_count": row.project_count or 0,
        "total_pv_kw": float(row.total_pv or 0),
        "total_battery_kwh": float(row.total_battery or 0),
        "total_consumption_kwh": float(row.total_consumption or 0),
    }


@router.get("/performance-kpis")
async def get_performance_kpis(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Performance-KPIs über alle Projekte
    """
    # Get all completed simulations for user's projects
    query = select(Simulation).join(Project).where(
        Project.user_id == current_user.id,
        Simulation.status == "completed"
    )
    result = await db.execute(query)
    simulations = result.scalars().all()

    if not simulations:
        return {
            "avg_autonomy_percent": None,
            "avg_self_consumption_percent": None,
            "total_pv_generation_kwh": 0,
            "total_self_consumption_kwh": 0,
            "total_grid_export_kwh": 0,
            "total_grid_import_kwh": 0,
            "total_annual_savings_eur": 0,
            "avg_payback_years": None,
            "total_co2_savings_kg": 0,
        }

    total_pv_gen = sum(s.pv_generation_kwh or 0 for s in simulations)
    total_self = sum(s.self_consumption_kwh or 0 for s in simulations)
    total_export = sum(s.grid_export_kwh or 0 for s in simulations)
    total_import = sum(s.grid_import_kwh or 0 for s in simulations)
    total_savings = sum(s.annual_savings_eur or 0 for s in simulations)

    autonomy_values = [s.autonomy_degree_percent for s in simulations if s.autonomy_degree_percent]
    self_consumption_values = [s.self_consumption_rate for s in simulations if s.self_consumption_rate]
    payback_values = [s.payback_period_years for s in simulations if s.payback_period_years]

    # CO2 savings (rough estimate: 400g CO2/kWh for German grid)
    co2_per_kwh = 0.4  # kg
    total_co2 = (total_self + total_export) * co2_per_kwh

    return {
        "avg_autonomy_percent": sum(autonomy_values) / len(autonomy_values) if autonomy_values else None,
        "avg_self_consumption_percent": sum(self_consumption_values) / len(self_consumption_values) if self_consumption_values else None,
        "total_pv_generation_kwh": total_pv_gen,
        "total_self_consumption_kwh": total_self,
        "total_grid_export_kwh": total_export,
        "total_grid_import_kwh": total_import,
        "total_annual_savings_eur": total_savings,
        "avg_payback_years": sum(payback_values) / len(payback_values) if payback_values else None,
        "total_co2_savings_kg": total_co2,
    }


# ============ HELPER FUNCTIONS ============

async def _get_simulation_metrics(db: AsyncSession, user_id) -> dict:
    """Get aggregated simulation metrics for user's projects"""
    query = select(Simulation).join(Project).where(
        Project.user_id == user_id,
        Simulation.status == "completed"
    )
    result = await db.execute(query)
    simulations = result.scalars().all()

    if not simulations:
        return {}

    autonomy_values = [s.autonomy_degree_percent for s in simulations if s.autonomy_degree_percent]
    savings_values = [s.annual_savings_eur for s in simulations if s.annual_savings_eur]
    investment_values = [s.total_investment_eur for s in simulations if s.total_investment_eur]
    payback_values = [s.payback_period_years for s in simulations if s.payback_period_years]

    return {
        "avg_autonomy": sum(autonomy_values) / len(autonomy_values) if autonomy_values else None,
        "total_savings": sum(savings_values) if savings_values else None,
        "total_investment": sum(investment_values) if investment_values else None,
        "avg_payback": sum(payback_values) / len(payback_values) if payback_values else None,
    }


async def _get_recent_projects(db: AsyncSession, user_id, limit: int = 5) -> List[ProjectSummary]:
    """Get recent projects with latest simulation data"""
    query = select(Project).where(
        Project.user_id == user_id
    ).order_by(Project.created_at.desc()).limit(limit)

    result = await db.execute(query)
    projects = result.scalars().all()

    summaries = []
    for project in projects:
        # Get latest simulation for project
        sim_query = select(Simulation).where(
            Simulation.project_id == project.id,
            Simulation.status == "completed"
        ).order_by(Simulation.created_at.desc()).limit(1)
        sim_result = await db.execute(sim_query)
        simulation = sim_result.scalar_one_or_none()

        summaries.append(ProjectSummary(
            id=str(project.id),
            customer_name=project.customer_name,
            project_name=project.project_name,
            pv_kw=project.pv_peak_power_kw or 0,
            battery_kwh=project.battery_capacity_kwh or 0,
            status=project.status or "draft",
            autonomy_percent=simulation.autonomy_degree_percent if simulation else None,
            annual_savings_eur=simulation.annual_savings_eur if simulation else None,
            created_at=project.created_at,
        ))

    return summaries


async def _get_monthly_trends(db: AsyncSession, user_id, months: int = 6) -> List[MonthlyTrend]:
    """Get monthly project creation trends"""
    trends = []
    now = datetime.utcnow()

    for i in range(months - 1, -1, -1):
        # Calculate month boundaries
        month_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)

        # Query projects created in this month
        query = select(Project).where(
            Project.user_id == user_id,
            Project.created_at >= month_start,
            Project.created_at < month_end
        )
        result = await db.execute(query)
        projects = result.scalars().all()

        trends.append(MonthlyTrend(
            month=month_start.strftime("%Y-%m"),
            projects_created=len(projects),
            total_pv_kw=sum(p.pv_peak_power_kw or 0 for p in projects),
            total_battery_kwh=sum(p.battery_capacity_kwh or 0 for p in projects),
        ))

    return trends


async def _get_offer_counts(db: AsyncSession, user_id) -> dict:
    """Get offer status counts"""
    query = select(Offer).join(Simulation).join(Project).where(
        Project.user_id == user_id
    )
    result = await db.execute(query)
    offers = result.scalars().all()

    return {
        "pending": sum(1 for o in offers if o.status in ("draft", "sent")),
        "signed": sum(1 for o in offers if o.status == "signed"),
        "total": len(offers),
    }
