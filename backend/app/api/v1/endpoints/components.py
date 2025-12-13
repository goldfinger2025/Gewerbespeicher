"""
Components Endpoints
Component catalog for inverters, batteries, PV modules
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional, List, Dict

router = APIRouter()


# ============ PYDANTIC MODELS ============

class ComponentResponse(BaseModel):
    id: str
    category: str
    subcategory: Optional[str] = None
    manufacturer: str
    model: str
    description: Optional[str] = None
    specification: Dict
    unit_price_eur: float
    availability_status: str


# ============ SAMPLE DATA ============

SAMPLE_COMPONENTS = [
    # Batteries
    {
        "id": "bat-001",
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
        "id": "bat-002",
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
        "id": "bat-003",
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
    
    # Inverters
    {
        "id": "inv-001",
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
        "id": "inv-002",
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
        "id": "inv-003",
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
    
    # PV Modules
    {
        "id": "pv-001",
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
        "id": "pv-002",
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


# ============ ENDPOINTS ============

@router.get("", response_model=List[ComponentResponse])
async def list_components(
    category: Optional[str] = Query(None, description="Filter by category"),
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price")
):
    """
    List all components with optional filters
    """
    components = SAMPLE_COMPONENTS
    
    # Apply filters
    if category:
        components = [c for c in components if c["category"] == category]
    
    if manufacturer:
        components = [c for c in components if c["manufacturer"].lower() == manufacturer.lower()]
    
    if min_price is not None:
        components = [c for c in components if c["unit_price_eur"] >= min_price]
    
    if max_price is not None:
        components = [c for c in components if c["unit_price_eur"] <= max_price]
    
    return [ComponentResponse(**c) for c in components]


@router.get("/{component_id}", response_model=ComponentResponse)
async def get_component(component_id: str):
    """
    Get component details by ID
    """
    for component in SAMPLE_COMPONENTS:
        if component["id"] == component_id:
            return ComponentResponse(**component)
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Komponente nicht gefunden")


@router.get("/categories/list")
async def list_categories():
    """
    List all available component categories
    """
    categories = set(c["category"] for c in SAMPLE_COMPONENTS)
    return {"categories": sorted(categories)}


@router.get("/manufacturers/list")
async def list_manufacturers():
    """
    List all available manufacturers
    """
    manufacturers = set(c["manufacturer"] for c in SAMPLE_COMPONENTS)
    return {"manufacturers": sorted(manufacturers)}
