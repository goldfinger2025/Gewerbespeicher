"""
Analytics Endpoints
Dashboard-Metriken und Portfolio-Übersicht
Phase 4: Advanced Analytics für Enterprise
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import csv
import io

from app.database import get_db
from app.models.user import User
from app.models.tenant import Tenant
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


# ============ PHASE 4: ADVANCED ANALYTICS ============

class TenantAnalytics(BaseModel):
    """Tenant-wide analytics for enterprise dashboards"""
    tenant_id: str
    tenant_name: str
    total_users: int
    total_projects: int
    projects_by_status: dict
    total_pv_capacity_kw: float
    total_battery_capacity_kwh: float
    total_annual_savings_eur: float
    avg_autonomy_percent: Optional[float]
    conversion_rate_percent: float
    avg_project_value_eur: Optional[float]
    period_comparison: dict


class UserPerformance(BaseModel):
    """Individual user performance metrics"""
    user_id: str
    user_name: str
    email: str
    projects_count: int
    offers_created: int
    offers_signed: int
    conversion_rate: float
    total_revenue_eur: float


class ConversionFunnel(BaseModel):
    """Sales funnel metrics"""
    total_leads: int
    simulations_run: int
    offers_created: int
    offers_sent: int
    offers_signed: int
    lead_to_simulation: float
    simulation_to_offer: float
    offer_to_signed: float
    overall_conversion: float


class ExportFormat(BaseModel):
    """Export configuration"""
    format: str = "csv"  # csv, excel
    include_projects: bool = True
    include_simulations: bool = True
    include_offers: bool = True
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


@router.get("/tenant", response_model=TenantAnalytics)
async def get_tenant_analytics(
    period: str = "month",  # week, month, quarter, year
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get tenant-wide analytics (admin/manager only)

    Provides aggregated metrics across all users in the tenant.
    """
    if not current_user.can_view_analytics():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keine Berechtigung für Tenant-Analytics"
        )

    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Benutzer ist keinem Tenant zugeordnet"
        )

    # Get tenant info
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant nicht gefunden")

    # Calculate period boundaries
    now = datetime.utcnow()
    if period == "week":
        current_start = now - timedelta(days=7)
        previous_start = current_start - timedelta(days=7)
    elif period == "quarter":
        current_start = now - timedelta(days=90)
        previous_start = current_start - timedelta(days=90)
    elif period == "year":
        current_start = now - timedelta(days=365)
        previous_start = current_start - timedelta(days=365)
    else:  # month
        current_start = now - timedelta(days=30)
        previous_start = current_start - timedelta(days=30)

    # Get all tenant users
    users_result = await db.execute(
        select(User).where(User.tenant_id == current_user.tenant_id)
    )
    users = users_result.scalars().all()
    user_ids = [u.id for u in users]

    # Get projects for tenant users
    projects_query = select(Project).where(Project.user_id.in_(user_ids))
    projects_result = await db.execute(projects_query)
    all_projects = projects_result.scalars().all()

    # Current period projects
    current_projects = [p for p in all_projects if p.created_at and p.created_at >= current_start]
    previous_projects = [p for p in all_projects
                        if p.created_at and previous_start <= p.created_at < current_start]

    # Calculate metrics
    total_pv = sum(p.pv_peak_power_kw or 0 for p in all_projects)
    total_battery = sum(p.battery_capacity_kwh or 0 for p in all_projects)

    # Projects by status
    status_counts = {}
    for p in all_projects:
        proj_status = p.status or "draft"
        status_counts[proj_status] = status_counts.get(proj_status, 0) + 1

    # Get simulations and calculate savings
    sims_result = await db.execute(
        select(Simulation).join(Project).where(
            Project.user_id.in_(user_ids),
            Simulation.status == "completed"
        )
    )
    simulations = sims_result.scalars().all()

    total_savings = sum(s.annual_savings_eur or 0 for s in simulations)
    autonomy_values = [s.autonomy_degree_percent for s in simulations if s.autonomy_degree_percent]
    avg_autonomy = sum(autonomy_values) / len(autonomy_values) if autonomy_values else None

    # Get offers for conversion rate
    offers_result = await db.execute(
        select(Offer).join(Simulation).join(Project).where(
            Project.user_id.in_(user_ids)
        )
    )
    offers = offers_result.scalars().all()
    signed_offers = [o for o in offers if o.status == "signed"]

    conversion_rate = (len(signed_offers) / len(offers) * 100) if offers else 0

    # Calculate average project value
    investment_values = [s.total_investment_eur for s in simulations if s.total_investment_eur]
    avg_value = sum(investment_values) / len(investment_values) if investment_values else None

    # Period comparison
    period_comparison = {
        "current_projects": len(current_projects),
        "previous_projects": len(previous_projects),
        "growth_percent": (
            ((len(current_projects) - len(previous_projects)) / len(previous_projects) * 100)
            if previous_projects else 0
        ),
        "current_pv_kw": sum(p.pv_peak_power_kw or 0 for p in current_projects),
        "previous_pv_kw": sum(p.pv_peak_power_kw or 0 for p in previous_projects),
    }

    return TenantAnalytics(
        tenant_id=str(tenant.id),
        tenant_name=tenant.name,
        total_users=len(users),
        total_projects=len(all_projects),
        projects_by_status=status_counts,
        total_pv_capacity_kw=total_pv,
        total_battery_capacity_kwh=total_battery,
        total_annual_savings_eur=total_savings,
        avg_autonomy_percent=avg_autonomy,
        conversion_rate_percent=round(conversion_rate, 1),
        avg_project_value_eur=avg_value,
        period_comparison=period_comparison,
    )


@router.get("/users", response_model=List[UserPerformance])
async def get_user_performance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get performance metrics for all users in tenant (admin only)
    """
    if not current_user.can_manage_users():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keine Berechtigung für Benutzer-Analytics"
        )

    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Benutzer ist keinem Tenant zugeordnet"
        )

    # Get all tenant users
    users_result = await db.execute(
        select(User).where(User.tenant_id == current_user.tenant_id)
    )
    users = users_result.scalars().all()

    performance_list = []
    for user in users:
        # Get user's projects
        projects_result = await db.execute(
            select(Project).where(Project.user_id == user.id)
        )
        projects = projects_result.scalars().all()

        # Get user's offers
        offers_result = await db.execute(
            select(Offer).join(Simulation).join(Project).where(
                Project.user_id == user.id
            )
        )
        offers = offers_result.scalars().all()
        signed = [o for o in offers if o.status == "signed"]

        # Calculate revenue from signed offers
        total_revenue = 0
        for offer in signed:
            if offer.pricing_breakdown and isinstance(offer.pricing_breakdown, dict):
                total_revenue += offer.pricing_breakdown.get("total_gross", 0)

        conversion = (len(signed) / len(offers) * 100) if offers else 0

        performance_list.append(UserPerformance(
            user_id=str(user.id),
            user_name=user.full_name or user.email,
            email=user.email,
            projects_count=len(projects),
            offers_created=len(offers),
            offers_signed=len(signed),
            conversion_rate=round(conversion, 1),
            total_revenue_eur=total_revenue,
        ))

    # Sort by revenue descending
    performance_list.sort(key=lambda x: x.total_revenue_eur, reverse=True)
    return performance_list


@router.get("/funnel", response_model=ConversionFunnel)
async def get_conversion_funnel(
    period: str = "month",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get sales conversion funnel metrics
    """
    if not current_user.can_view_analytics():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keine Berechtigung für Funnel-Analytics"
        )

    # Calculate period
    now = datetime.utcnow()
    if period == "week":
        start_date = now - timedelta(days=7)
    elif period == "quarter":
        start_date = now - timedelta(days=90)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=30)

    # Get user IDs based on tenant
    if current_user.tenant_id:
        users_result = await db.execute(
            select(User.id).where(User.tenant_id == current_user.tenant_id)
        )
        user_ids = [r[0] for r in users_result.all()]
    else:
        user_ids = [current_user.id]

    # Count projects (leads)
    projects_result = await db.execute(
        select(func.count(Project.id)).where(
            Project.user_id.in_(user_ids),
            Project.created_at >= start_date
        )
    )
    total_leads = projects_result.scalar() or 0

    # Count simulations
    sims_result = await db.execute(
        select(func.count(Simulation.id)).join(Project).where(
            Project.user_id.in_(user_ids),
            Simulation.created_at >= start_date
        )
    )
    simulations_run = sims_result.scalar() or 0

    # Count offers by status
    offers_base = select(Offer).join(Simulation).join(Project).where(
        Project.user_id.in_(user_ids),
        Offer.created_at >= start_date
    )
    offers_result = await db.execute(offers_base)
    all_offers = offers_result.scalars().all()

    offers_created = len(all_offers)
    offers_sent = len([o for o in all_offers if o.status in ("sent", "viewed", "signed")])
    offers_signed = len([o for o in all_offers if o.status == "signed"])

    # Calculate conversion rates
    lead_to_sim = (simulations_run / total_leads * 100) if total_leads else 0
    sim_to_offer = (offers_created / simulations_run * 100) if simulations_run else 0
    offer_to_signed = (offers_signed / offers_sent * 100) if offers_sent else 0
    overall = (offers_signed / total_leads * 100) if total_leads else 0

    return ConversionFunnel(
        total_leads=total_leads,
        simulations_run=simulations_run,
        offers_created=offers_created,
        offers_sent=offers_sent,
        offers_signed=offers_signed,
        lead_to_simulation=round(lead_to_sim, 1),
        simulation_to_offer=round(sim_to_offer, 1),
        offer_to_signed=round(offer_to_signed, 1),
        overall_conversion=round(overall, 1),
    )


@router.get("/export")
async def export_analytics_data(
    format: str = "csv",
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export analytics data as CSV or Excel

    Parameters:
    - format: "csv" (default) or "excel"
    - date_from: Start date filter
    - date_to: End date filter
    """
    if not current_user.can_view_analytics():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keine Berechtigung für Datenexport"
        )

    # Set date range
    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        date_from = date_to - timedelta(days=365)

    # Get user IDs based on tenant
    if current_user.tenant_id:
        users_result = await db.execute(
            select(User).where(User.tenant_id == current_user.tenant_id)
        )
        users = {u.id: u for u in users_result.scalars().all()}
        user_ids = list(users.keys())
    else:
        users = {current_user.id: current_user}
        user_ids = [current_user.id]

    # Get projects
    projects_result = await db.execute(
        select(Project).where(
            Project.user_id.in_(user_ids),
            Project.created_at >= date_from,
            Project.created_at <= date_to
        ).order_by(Project.created_at.desc())
    )
    projects = projects_result.scalars().all()

    # Build CSV data
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    # Header
    writer.writerow([
        "Projekt-ID",
        "Kunde",
        "Firma",
        "PLZ",
        "Stadt",
        "Erstellt am",
        "Status",
        "PV-Leistung (kWp)",
        "Speicher (kWh)",
        "Jahresverbrauch (kWh)",
        "Autarkiegrad (%)",
        "Jährl. Einsparung (EUR)",
        "Amortisation (Jahre)",
        "Angebot-Status",
        "Bearbeiter"
    ])

    # Data rows
    for project in projects:
        # Get latest simulation
        sim_result = await db.execute(
            select(Simulation).where(
                Simulation.project_id == project.id,
                Simulation.status == "completed"
            ).order_by(Simulation.created_at.desc()).limit(1)
        )
        sim = sim_result.scalar_one_or_none()

        # Get offer status
        offer_result = await db.execute(
            select(Offer).join(Simulation).where(
                Simulation.project_id == project.id
            ).order_by(Offer.created_at.desc()).limit(1)
        )
        offer = offer_result.scalar_one_or_none()

        user = users.get(project.user_id)

        writer.writerow([
            str(project.id),
            project.customer_name,
            project.customer_company or "",
            project.postal_code or "",
            project.city or "",
            project.created_at.strftime("%Y-%m-%d") if project.created_at else "",
            project.status or "draft",
            project.pv_peak_power_kw or 0,
            project.battery_capacity_kwh or 0,
            project.annual_consumption_kwh or 0,
            sim.autonomy_degree_percent if sim else "",
            sim.annual_savings_eur if sim else "",
            sim.payback_period_years if sim else "",
            offer.status if offer else "",
            user.full_name if user else "",
        ])

    output.seek(0)

    filename = f"analytics_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/comparison")
async def get_period_comparison(
    period1_start: datetime,
    period1_end: datetime,
    period2_start: datetime,
    period2_end: datetime,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Compare metrics between two time periods
    """
    if not current_user.can_view_analytics():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keine Berechtigung für Vergleichs-Analytics"
        )

    # Get user IDs based on tenant
    if current_user.tenant_id:
        users_result = await db.execute(
            select(User.id).where(User.tenant_id == current_user.tenant_id)
        )
        user_ids = [r[0] for r in users_result.all()]
    else:
        user_ids = [current_user.id]

    async def get_period_metrics(start: datetime, end: datetime) -> dict:
        # Projects
        projects_result = await db.execute(
            select(Project).where(
                Project.user_id.in_(user_ids),
                Project.created_at >= start,
                Project.created_at <= end
            )
        )
        projects = projects_result.scalars().all()

        # Simulations
        sims_result = await db.execute(
            select(Simulation).join(Project).where(
                Project.user_id.in_(user_ids),
                Simulation.created_at >= start,
                Simulation.created_at <= end,
                Simulation.status == "completed"
            )
        )
        sims = sims_result.scalars().all()

        # Offers
        offers_result = await db.execute(
            select(Offer).join(Simulation).join(Project).where(
                Project.user_id.in_(user_ids),
                Offer.created_at >= start,
                Offer.created_at <= end
            )
        )
        offers = offers_result.scalars().all()

        return {
            "projects_created": len(projects),
            "total_pv_kw": sum(p.pv_peak_power_kw or 0 for p in projects),
            "total_battery_kwh": sum(p.battery_capacity_kwh or 0 for p in projects),
            "simulations_run": len(sims),
            "avg_autonomy": (
                sum(s.autonomy_degree_percent or 0 for s in sims) / len(sims)
                if sims else 0
            ),
            "total_savings": sum(s.annual_savings_eur or 0 for s in sims),
            "offers_created": len(offers),
            "offers_signed": len([o for o in offers if o.status == "signed"]),
        }

    period1 = await get_period_metrics(period1_start, period1_end)
    period2 = await get_period_metrics(period2_start, period2_end)

    # Calculate changes
    def calc_change(new_val, old_val):
        if old_val == 0:
            return 100 if new_val > 0 else 0
        return round((new_val - old_val) / old_val * 100, 1)

    return {
        "period1": {
            "start": period1_start.isoformat(),
            "end": period1_end.isoformat(),
            "metrics": period1,
        },
        "period2": {
            "start": period2_start.isoformat(),
            "end": period2_end.isoformat(),
            "metrics": period2,
        },
        "changes": {
            "projects_change_percent": calc_change(period1["projects_created"], period2["projects_created"]),
            "pv_change_percent": calc_change(period1["total_pv_kw"], period2["total_pv_kw"]),
            "savings_change_percent": calc_change(period1["total_savings"], period2["total_savings"]),
            "conversion_change_percent": calc_change(
                period1["offers_signed"] / period1["offers_created"] * 100 if period1["offers_created"] else 0,
                period2["offers_signed"] / period2["offers_created"] * 100 if period2["offers_created"] else 0
            ),
        }
    }
