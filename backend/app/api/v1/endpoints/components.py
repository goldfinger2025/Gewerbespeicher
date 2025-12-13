"""
Components Endpoints
Component catalog for inverters, batteries, PV modules
"""

from fastapi import APIRouter, Query, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.database import get_db
from app.models.component import Component
from app.crud import component as component_crud
from app.api.deps import get_current_admin_user, get_optional_current_user
from app.models.user import User


router = APIRouter()


# ============ PYDANTIC MODELS ============

class ComponentResponse(BaseModel):
    id: str
    category: str
    subcategory: Optional[str] = None
    manufacturer: str
    model: str
    description: Optional[str] = None
    specification: Optional[Dict[str, Any]] = None
    unit_price_eur: Optional[float] = None
    availability_status: Optional[str] = None

    class Config:
        from_attributes = True


class ComponentListResponse(BaseModel):
    total: int
    items: List[ComponentResponse]


class ComponentCreate(BaseModel):
    category: str
    subcategory: Optional[str] = None
    manufacturer: str
    model: str
    description: Optional[str] = None
    specification: Optional[Dict[str, Any]] = None
    unit_price_eur: Optional[float] = None
    supplier_sku: Optional[str] = None
    availability_status: Optional[str] = "in_stock"


class ComponentUpdate(BaseModel):
    category: Optional[str] = None
    subcategory: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    description: Optional[str] = None
    specification: Optional[Dict[str, Any]] = None
    unit_price_eur: Optional[float] = None
    supplier_sku: Optional[str] = None
    availability_status: Optional[str] = None


# ============ SAMPLE DATA (for seeding) ============

SAMPLE_COMPONENTS = [
    {
        "category": "battery",
        "subcategory": "commercial",
        "manufacturer": "BYD",
        "model": "Battery-Box Premium HVS 12.8",
        "description": "Hochvolt-Speicher für Gewerbe",
        "specification": {
            "capacity_kwh": 12.8,
            "voltage_v": 409.6,
            "cycles": 6000,
            "chemistry": "LFP",
            "warranty_years": 10
        },
        "unit_price_eur": 5500.00,
        "availability_status": "in_stock"
    },
    {
        "category": "battery",
        "subcategory": "commercial",
        "manufacturer": "Huawei",
        "model": "LUNA2000-15-S0",
        "description": "Modularer Gewerbespeicher",
        "specification": {
            "capacity_kwh": 15.0,
            "voltage_v": 600,
            "cycles": 4000,
            "chemistry": "LFP",
            "warranty_years": 10
        },
        "unit_price_eur": 6200.00,
        "availability_status": "in_stock"
    },
    {
        "category": "battery",
        "subcategory": "large_scale",
        "manufacturer": "SolarEdge",
        "model": "Energy Bank 48kWh",
        "description": "Großspeicher für Industrie",
        "specification": {
            "capacity_kwh": 48.0,
            "voltage_v": 400,
            "cycles": 5000,
            "chemistry": "LFP",
            "warranty_years": 10
        },
        "unit_price_eur": 18500.00,
        "availability_status": "on_order"
    },
    {
        "category": "inverter",
        "subcategory": "hybrid",
        "manufacturer": "Fronius",
        "model": "Symo GEN24 10.0 Plus",
        "description": "Hybrid-Wechselrichter mit Speicheranbindung",
        "specification": {
            "power_kw": 10.0,
            "efficiency_percent": 97.6,
            "mppt_count": 2,
            "phases": 3
        },
        "unit_price_eur": 3200.00,
        "availability_status": "in_stock"
    },
    {
        "category": "inverter",
        "subcategory": "commercial",
        "manufacturer": "Huawei",
        "model": "SUN2000-50KTL-M3",
        "description": "Gewerbewechselrichter 50kW",
        "specification": {
            "power_kw": 50.0,
            "efficiency_percent": 98.6,
            "mppt_count": 6,
            "phases": 3
        },
        "unit_price_eur": 4800.00,
        "availability_status": "in_stock"
    },
    {
        "category": "inverter",
        "subcategory": "commercial",
        "manufacturer": "SMA",
        "model": "Sunny Tripower X 25",
        "description": "Dreiphasiger Stringwechselrichter",
        "specification": {
            "power_kw": 25.0,
            "efficiency_percent": 98.3,
            "mppt_count": 3,
            "phases": 3
        },
        "unit_price_eur": 3900.00,
        "availability_status": "in_stock"
    },
    {
        "category": "pv_module",
        "subcategory": "monocrystalline",
        "manufacturer": "Trina Solar",
        "model": "Vertex S+ TSM-445NEG9R.28",
        "description": "n-Type TOPCon Modul 445W",
        "specification": {
            "power_w": 445,
            "efficiency_percent": 22.0,
            "bifacial": True,
            "warranty_years": 25
        },
        "unit_price_eur": 165.00,
        "availability_status": "in_stock"
    },
    {
        "category": "pv_module",
        "subcategory": "monocrystalline",
        "manufacturer": "JA Solar",
        "model": "JAM72D40-565/GB",
        "description": "Bifaziales Modul 565W",
        "specification": {
            "power_w": 565,
            "efficiency_percent": 21.8,
            "bifacial": True,
            "warranty_years": 25
        },
        "unit_price_eur": 195.00,
        "availability_status": "in_stock"
    },
]


# ============ HELPER FUNCTIONS ============

def component_to_response(component: Component) -> ComponentResponse:
    """Convert SQLAlchemy Component model to Pydantic response"""
    return ComponentResponse(
        id=str(component.id),
        category=component.category,
        subcategory=component.subcategory,
        manufacturer=component.manufacturer,
        model=component.model,
        description=component.description,
        specification=component.specification,
        unit_price_eur=component.unit_price_eur,
        availability_status=component.availability_status,
    )


# ============ ENDPOINTS ============

@router.get("", response_model=ComponentListResponse)
async def list_components(
    category: Optional[str] = Query(None, description="Filter by category"),
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List all components with optional filters
    """
    components, total = await component_crud.get_components(
        db=db,
        skip=skip,
        limit=limit,
        category=category,
        manufacturer=manufacturer,
        min_price=min_price,
        max_price=max_price,
    )

    return ComponentListResponse(
        total=total,
        items=[component_to_response(c) for c in components]
    )


@router.get("/categories/list")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """
    List all available component categories
    """
    components, _ = await component_crud.get_components(db=db, limit=1000)
    categories = set(c.category for c in components)
    return {"categories": sorted(categories)}


@router.get("/manufacturers/list")
async def list_manufacturers(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all available manufacturers
    """
    manufacturers = await component_crud.get_manufacturers(db=db, category=category)
    return {"manufacturers": manufacturers}


@router.get("/{component_id}", response_model=ComponentResponse)
async def get_component(
    component_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get component details by ID
    """
    try:
        uuid_id = UUID(component_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Komponenten-ID"
        )

    component = await component_crud.get_component_by_id(db=db, component_id=uuid_id)

    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Komponente nicht gefunden"
        )

    return component_to_response(component)


@router.post("", response_model=ComponentResponse, status_code=status.HTTP_201_CREATED)
async def create_component(
    component_data: ComponentCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new component (admin only)
    """
    component = await component_crud.create_component(
        db=db,
        category=component_data.category,
        manufacturer=component_data.manufacturer,
        model=component_data.model,
        subcategory=component_data.subcategory,
        description=component_data.description,
        specification=component_data.specification,
        unit_price_eur=component_data.unit_price_eur,
        supplier_sku=component_data.supplier_sku,
        availability_status=component_data.availability_status,
    )

    return component_to_response(component)


@router.patch("/{component_id}", response_model=ComponentResponse)
async def update_component(
    component_id: str,
    component_data: ComponentUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a component (admin only)
    """
    try:
        uuid_id = UUID(component_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Komponenten-ID"
        )

    component = await component_crud.get_component_by_id(db=db, component_id=uuid_id)

    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Komponente nicht gefunden"
        )

    update_data = component_data.model_dump(exclude_unset=True)

    updated_component = await component_crud.update_component(
        db=db,
        component=component,
        **update_data
    )

    return component_to_response(updated_component)


@router.delete("/{component_id}", status_code=status.HTTP_200_OK)
async def delete_component(
    component_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate a component (admin only)
    """
    try:
        uuid_id = UUID(component_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Komponenten-ID"
        )

    component = await component_crud.get_component_by_id(db=db, component_id=uuid_id)

    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Komponente nicht gefunden"
        )

    await component_crud.deactivate_component(db=db, component=component)

    return {"message": "Komponente deaktiviert", "id": component_id}


@router.post("/seed", status_code=status.HTTP_201_CREATED)
async def seed_components(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Seed database with sample components (admin only)
    """
    created = []

    for comp_data in SAMPLE_COMPONENTS:
        component = await component_crud.create_component(
            db=db,
            **comp_data
        )
        created.append(component_to_response(component))

    return {
        "message": f"{len(created)} Komponenten erstellt",
        "components": created
    }
