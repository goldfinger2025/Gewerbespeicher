"""
Project Endpoints
CRUD operations for PV+Storage projects
"""

from fastapi import APIRouter, HTTPException, Query, Depends, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID
import re

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.crud import project as project_crud
from app.api.deps import get_current_user


router = APIRouter()


# ============ GEOCODING HELPER ============

# German postal code regions with approximate center coordinates
# First digit of PLZ maps to region
PLZ_REGION_COORDS = {
    "0": (51.05, 13.74),   # Sachsen, Thüringen (Dresden area)
    "1": (52.52, 13.40),   # Berlin, Brandenburg
    "2": (53.55, 10.00),   # Hamburg, Schleswig-Holstein, Niedersachsen Nord
    "3": (52.37, 9.74),    # Niedersachsen, Sachsen-Anhalt
    "4": (51.96, 7.63),    # Nordrhein-Westfalen Nord
    "5": (50.94, 6.96),    # Nordrhein-Westfalen Süd (Köln area)
    "6": (50.11, 8.68),    # Hessen, Rheinland-Pfalz (Frankfurt area)
    "7": (48.78, 9.18),    # Baden-Württemberg (Stuttgart area)
    "8": (48.14, 11.58),   # Bayern (München area)
    "9": (49.45, 11.08),   # Bayern Nord (Nürnberg area)
}


def get_coordinates_from_plz(postal_code: str) -> tuple[float, float]:
    """
    Get approximate coordinates based on German postal code.
    Uses the first digit for region mapping and adds small variations
    based on the full postal code for differentiation.

    Args:
        postal_code: German 5-digit postal code

    Returns:
        Tuple of (latitude, longitude)
    """
    if not postal_code or len(postal_code) < 1:
        # Default: Germany center
        return (51.16, 10.45)

    first_digit = postal_code[0]
    base_lat, base_lon = PLZ_REGION_COORDS.get(first_digit, (51.16, 10.45))

    # Add small variation based on full PLZ for more accurate positioning
    try:
        plz_num = int(postal_code[:5]) if len(postal_code) >= 5 else int(postal_code)
        # Spread within ~0.5 degrees based on PLZ
        lat_offset = ((plz_num % 1000) - 500) / 1000 * 0.5
        lon_offset = ((plz_num % 500) - 250) / 500 * 0.5
        return (base_lat + lat_offset, base_lon + lon_offset)
    except ValueError:
        return (base_lat, base_lon)


# ============ PYDANTIC MODELS ============

class ProjectCreate(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=255, description="Kundenname")
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = Field(None, max_length=20)
    customer_company: Optional[str] = Field(None, max_length=255)
    address: str = Field(..., min_length=5, max_length=500, description="Adresse")
    postal_code: str = Field(..., pattern=r"^\d{5}$", description="Deutsche PLZ (5 Ziffern)")
    city: Optional[str] = Field(None, max_length=100)
    project_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    pv_peak_power_kw: float = Field(..., gt=0, le=10000, description="PV-Leistung in kWp (0.1-10000)")
    pv_orientation: Optional[Literal["north", "south", "east", "west", "north-east", "north-west", "south-east", "south-west"]] = "south"
    pv_tilt_angle: Optional[float] = Field(30.0, ge=0, le=90, description="Neigung in Grad (0-90)")
    roof_area_sqm: Optional[float] = Field(None, gt=0, le=100000)
    battery_capacity_kwh: float = Field(..., gt=0, le=100000, description="Speicherkapazität in kWh")
    battery_power_kw: Optional[float] = Field(None, gt=0, le=50000)
    battery_chemistry: Optional[Literal["lfp", "nmc", "lead-acid", "other"]] = None
    battery_manufacturer: Optional[str] = Field(None, max_length=100)
    annual_consumption_kwh: float = Field(..., gt=0, le=100000000, description="Jahresverbrauch in kWh")
    peak_load_kw: Optional[float] = Field(None, gt=0, le=50000)
    load_profile_type: Optional[Literal["office", "retail", "production", "warehouse"]] = "office"
    electricity_price_eur_kwh: Optional[float] = Field(0.30, ge=0.01, le=2.0)
    grid_fee_eur_kwh: Optional[float] = Field(None, ge=0, le=0.5)
    feed_in_tariff_eur_kwh: Optional[float] = Field(0.08, ge=0, le=0.5)

    @field_validator("customer_phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Remove spaces and check for valid phone format
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^\+?[\d]{6,20}$", cleaned):
            raise ValueError("Ungültige Telefonnummer")
        return v


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
    # Get coordinates from postal code
    # TODO: In production, use Google Maps API for exact geocoding
    latitude, longitude = get_coordinates_from_plz(project_data.postal_code)

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
