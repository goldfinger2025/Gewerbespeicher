"""
Project Endpoints
CRUD operations for PV+Storage projects
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import uuid4

router = APIRouter()


# ============ PYDANTIC MODELS ============

class ProjectCreate(BaseModel):
    customer_name: str
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    address: str
    postal_code: str
    city: Optional[str] = None
    project_name: Optional[str] = None
    pv_peak_power_kw: float
    pv_orientation: Optional[str] = "south"
    pv_tilt_angle: Optional[float] = 30.0
    battery_capacity_kwh: float
    battery_power_kw: Optional[float] = None
    annual_consumption_kwh: float
    electricity_price_eur_kwh: Optional[float] = 0.30


class ProjectUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    project_name: Optional[str] = None
    pv_peak_power_kw: Optional[float] = None
    battery_capacity_kwh: Optional[float] = None
    battery_power_kw: Optional[float] = None
    annual_consumption_kwh: Optional[float] = None
    electricity_price_eur_kwh: Optional[float] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    address: str
    postal_code: str
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    project_name: Optional[str] = None
    status: str = "draft"
    pv_peak_power_kw: float
    pv_orientation: Optional[str] = None
    pv_tilt_angle: Optional[float] = None
    battery_capacity_kwh: float
    battery_power_kw: Optional[float] = None
    annual_consumption_kwh: float
    electricity_price_eur_kwh: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    total: int
    items: List[ProjectResponse]


# ============ IN-MEMORY STORAGE (MVP) ============
# TODO: Replace with database in production

_projects_db: dict = {}


# ============ ENDPOINTS ============

@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(project: ProjectCreate):
    """
    Create a new project
    """
    project_id = str(uuid4())
    now = datetime.utcnow()
    
    # Geocoding placeholder (TODO: Use Google Maps API)
    # For now, use default coordinates for Schleswig-Holstein
    latitude = 54.5 + (hash(project.postal_code) % 100) / 1000
    longitude = 9.3 + (hash(project.address) % 100) / 1000
    
    # Calculate battery power if not provided (rule of thumb: ~0.5x capacity)
    battery_power = project.battery_power_kw or (project.battery_capacity_kwh * 0.5)
    
    db_project = {
        "id": project_id,
        "user_id": "user-demo",  # TODO: Get from JWT
        **project.model_dump(),
        "battery_power_kw": battery_power,
        "latitude": latitude,
        "longitude": longitude,
        "status": "draft",
        "created_at": now,
        "updated_at": now,
    }
    
    _projects_db[project_id] = db_project
    
    return ProjectResponse(**db_project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None
):
    """
    List all projects for current user
    """
    projects = list(_projects_db.values())
    
    # Filter by status if provided
    if status:
        projects = [p for p in projects if p.get("status") == status]
    
    # Sort by created_at descending
    projects.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Paginate
    total = len(projects)
    items = projects[skip:skip + limit]
    
    return ProjectListResponse(
        total=total,
        items=[ProjectResponse(**p) for p in items]
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """
    Get a specific project by ID
    """
    if project_id not in _projects_db:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    
    return ProjectResponse(**_projects_db[project_id])


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project: ProjectUpdate):
    """
    Update an existing project
    """
    if project_id not in _projects_db:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    
    db_project = _projects_db[project_id]
    
    # Update only provided fields
    update_data = project.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            db_project[key] = value
    
    db_project["updated_at"] = datetime.utcnow()
    _projects_db[project_id] = db_project
    
    return ProjectResponse(**db_project)


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """
    Delete a project
    """
    if project_id not in _projects_db:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    
    del _projects_db[project_id]
    
    return {"message": "Projekt gelöscht", "id": project_id}
