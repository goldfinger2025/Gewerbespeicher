"""
Project Endpoints
CRUD operations for PV+Storage projects
"""

from fastapi import APIRouter, HTTPException, Query, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.crud import project as project_crud
from app.api.deps import get_current_user


router = APIRouter()


# ============ PYDANTIC MODELS ============

class ProjectCreate(BaseModel):
    customer_name: str
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    customer_company: Optional[str] = None
    address: str
    postal_code: str
    city: Optional[str] = None
    project_name: Optional[str] = None
    description: Optional[str] = None
    pv_peak_power_kw: float
    pv_orientation: Optional[str] = "south"
    pv_tilt_angle: Optional[float] = 30.0
    roof_area_sqm: Optional[float] = None
    battery_capacity_kwh: float
    battery_power_kw: Optional[float] = None
    battery_chemistry: Optional[str] = None
    battery_manufacturer: Optional[str] = None
    annual_consumption_kwh: float
    peak_load_kw: Optional[float] = None
    load_profile_type: Optional[str] = "office"  # office, retail, production, warehouse
    electricity_price_eur_kwh: Optional[float] = 0.30
    grid_fee_eur_kwh: Optional[float] = None
    feed_in_tariff_eur_kwh: Optional[float] = 0.08


class ProjectUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    customer_company: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    project_name: Optional[str] = None
    description: Optional[str] = None
    pv_peak_power_kw: Optional[float] = None
    pv_orientation: Optional[str] = None
    pv_tilt_angle: Optional[float] = None
    roof_area_sqm: Optional[float] = None
    battery_capacity_kwh: Optional[float] = None
    battery_power_kw: Optional[float] = None
    battery_chemistry: Optional[str] = None
    battery_manufacturer: Optional[str] = None
    annual_consumption_kwh: Optional[float] = None
    peak_load_kw: Optional[float] = None
    load_profile_type: Optional[str] = None
    electricity_price_eur_kwh: Optional[float] = None
    grid_fee_eur_kwh: Optional[float] = None
    feed_in_tariff_eur_kwh: Optional[float] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_company: Optional[str] = None
    address: str
    postal_code: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    project_name: Optional[str] = None
    description: Optional[str] = None
    status: str = "draft"
    pv_peak_power_kw: Optional[float] = None
    pv_orientation: Optional[str] = None
    pv_tilt_angle: Optional[float] = None
    roof_area_sqm: Optional[float] = None
    battery_capacity_kwh: Optional[float] = None
    battery_power_kw: Optional[float] = None
    battery_chemistry: Optional[str] = None
    battery_manufacturer: Optional[str] = None
    annual_consumption_kwh: Optional[float] = None
    peak_load_kw: Optional[float] = None
    load_profile_type: Optional[str] = "office"
    electricity_price_eur_kwh: Optional[float] = None
    grid_fee_eur_kwh: Optional[float] = None
    feed_in_tariff_eur_kwh: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    total: int
    items: List[ProjectResponse]


# ============ HELPER FUNCTIONS ============

def project_to_response(project: Project) -> ProjectResponse:
    """Convert SQLAlchemy Project model to Pydantic response"""
    return ProjectResponse(
        id=str(project.id),
        user_id=str(project.user_id),
        customer_name=project.customer_name,
        customer_email=project.customer_email,
        customer_phone=project.customer_phone,
        customer_company=project.customer_company,
        address=project.address,
        postal_code=project.postal_code,
        city=project.city,
        latitude=project.latitude,
        longitude=project.longitude,
        project_name=project.project_name,
        description=project.description,
        status=project.status,
        pv_peak_power_kw=project.pv_peak_power_kw,
        pv_orientation=project.pv_orientation,
        pv_tilt_angle=project.pv_tilt_angle,
        roof_area_sqm=project.roof_area_sqm,
        battery_capacity_kwh=project.battery_capacity_kwh,
        battery_power_kw=project.battery_power_kw,
        battery_chemistry=project.battery_chemistry,
        battery_manufacturer=project.battery_manufacturer,
        annual_consumption_kwh=project.annual_consumption_kwh,
        peak_load_kw=project.peak_load_kw,
        load_profile_type=project.load_profile_type or "office",
        electricity_price_eur_kwh=project.electricity_price_eur_kwh,
        grid_fee_eur_kwh=project.grid_fee_eur_kwh,
        feed_in_tariff_eur_kwh=project.feed_in_tariff_eur_kwh,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


# ============ ENDPOINTS ============

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new project
    """
    # Geocoding placeholder (TODO: Use Google Maps API)
    # For now, use default coordinates for Schleswig-Holstein
    latitude = 54.5 + (hash(project_data.postal_code) % 100) / 1000
    longitude = 9.3 + (hash(project_data.address) % 100) / 1000

    project = await project_crud.create_project(
        db=db,
        user_id=current_user.id,
        customer_name=project_data.customer_name,
        address=project_data.address,
        postal_code=project_data.postal_code,
        pv_peak_power_kw=project_data.pv_peak_power_kw,
        battery_capacity_kwh=project_data.battery_capacity_kwh,
        annual_consumption_kwh=project_data.annual_consumption_kwh,
        customer_email=project_data.customer_email,
        customer_phone=project_data.customer_phone,
        customer_company=project_data.customer_company,
        city=project_data.city,
        project_name=project_data.project_name,
        description=project_data.description,
        pv_orientation=project_data.pv_orientation,
        pv_tilt_angle=project_data.pv_tilt_angle,
        roof_area_sqm=project_data.roof_area_sqm,
        battery_power_kw=project_data.battery_power_kw,
        battery_chemistry=project_data.battery_chemistry,
        battery_manufacturer=project_data.battery_manufacturer,
        peak_load_kw=project_data.peak_load_kw,
        load_profile_type=project_data.load_profile_type,
        electricity_price_eur_kwh=project_data.electricity_price_eur_kwh,
        grid_fee_eur_kwh=project_data.grid_fee_eur_kwh,
        feed_in_tariff_eur_kwh=project_data.feed_in_tariff_eur_kwh,
        latitude=latitude,
        longitude=longitude,
    )

    return project_to_response(project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all projects for current user
    """
    projects, total = await project_crud.get_projects_by_user(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        status=status,
    )

    return ProjectListResponse(
        total=total,
        items=[project_to_response(p) for p in projects]
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific project by ID
    """
    try:
        uuid_id = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Projekt-ID"
        )

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

    return project_to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing project
    """
    try:
        uuid_id = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Projekt-ID"
        )

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

    # Update only provided fields
    update_data = project_data.model_dump(exclude_unset=True)

    updated_project = await project_crud.update_project(
        db=db,
        project=project,
        **update_data
    )

    return project_to_response(updated_project)


@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a project
    """
    try:
        uuid_id = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Projekt-ID"
        )

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

    await project_crud.delete_project(db=db, project=project)

    return {"message": "Projekt gelöscht", "id": project_id}
