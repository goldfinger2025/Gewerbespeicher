"""
Offer Endpoints
Generate and manage quotes/offers with Claude AI integration
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.claude_service import get_claude_service

router = APIRouter()


# ============ PYDANTIC MODELS ============

class OfferCreate(BaseModel):
    simulation_id: str
    generate_pdf: Optional[bool] = True
    send_to_customer: Optional[bool] = False


class OfferResponse(BaseModel):
    id: str
    simulation_id: str
    project_id: str
    offer_number: str
    offer_text: Optional[str] = None
    pdf_path: Optional[str] = None
    is_signed: bool = False
    valid_until: datetime
    status: str  # draft, sent, viewed, signed, completed, rejected
    created_at: datetime


# ============ IN-MEMORY STORAGE (MVP) ============

_offers_db: dict = {}
_offer_counter: int = 1000

# Import simulations storage
from app.api.v1.endpoints.simulations import _simulations_db
from app.api.v1.endpoints.projects import _projects_db


# ============ ENDPOINTS ============

@router.post("", response_model=OfferResponse, status_code=201)
async def create_offer(request: OfferCreate):
    """
    Create a new offer from simulation results
    Uses Claude AI to generate professional offer text
    """
    global _offer_counter
    
    # Get simulation
    if request.simulation_id not in _simulations_db:
        raise HTTPException(status_code=404, detail="Simulation nicht gefunden")
    
    simulation = _simulations_db[request.simulation_id]
    
    # Get project
    project_id = simulation["project_id"]
    if project_id not in _projects_db:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    
    project = _projects_db[project_id]
    
    # Generate offer
    offer_id = str(uuid4())
    _offer_counter += 1
    offer_number = f"EWS-{datetime.now().year}-{_offer_counter:04d}"
    
    now = datetime.utcnow()
    valid_until = now + timedelta(days=30)  # 30 days validity
    
    # Get simulation results
    results = simulation.get("results", {})
    if hasattr(results, "model_dump"):
        results = results.model_dump()
    
    # Use Claude to generate offer text
    claude = get_claude_service()
    try:
        offer_text = await claude.generate_offer_text(
            project=project,
            simulation=results,
            components=None
        )
    except Exception as e:
        # Fallback to basic text if Claude fails
        offer_text = _generate_fallback_offer_text(project, results)
    
    offer = {
        "id": offer_id,
        "simulation_id": request.simulation_id,
        "project_id": project_id,
        "offer_number": offer_number,
        "offer_text": offer_text,
        "pdf_path": None,  # TODO: Generate PDF
        "is_signed": False,
        "valid_until": valid_until,
        "status": "draft",
        "created_at": now,
    }
    
    _offers_db[offer_id] = offer
    
    return OfferResponse(**offer)


def _generate_fallback_offer_text(project: dict, results: dict) -> str:
    """Fallback offer text if Claude is unavailable"""
    return f"""
Sehr geehrte/r {project.get('customer_name', 'Kunde')},

vielen Dank für Ihr Interesse an einer PV-Speicherlösung.

**Ihre Systemkonfiguration:**
- PV-Leistung: {project.get('pv_peak_power_kw', 0)} kWp
- Speicherkapazität: {project.get('battery_capacity_kwh', 0)} kWh

**Simulationsergebnisse:**
- Autarkiegrad: {results.get('autonomy_degree_percent', 0):.0f}%
- Jährliche Einsparung: {results.get('annual_savings_eur', 0):,.0f} €
- Amortisation: {results.get('payback_period_years', 0):.1f} Jahre

Gerne beraten wir Sie persönlich zu diesem Angebot.

Mit freundlichen Grüßen,
Ihr EWS Team
"""


@router.get("/{offer_id}", response_model=OfferResponse)
async def get_offer(offer_id: str):
    """
    Get offer details
    """
    if offer_id not in _offers_db:
        raise HTTPException(status_code=404, detail="Angebot nicht gefunden")
    
    return OfferResponse(**_offers_db[offer_id])


@router.get("/{offer_id}/preview")
async def get_offer_preview(offer_id: str):
    """
    Get HTML preview of offer
    """
    if offer_id not in _offers_db:
        raise HTTPException(status_code=404, detail="Angebot nicht gefunden")
    
    offer = _offers_db[offer_id]
    
    # Return HTML preview
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Angebot {offer['offer_number']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; }}
            h1 {{ color: #1e40af; }}
            .meta {{ color: #64748b; margin-bottom: 20px; }}
            .content {{ white-space: pre-wrap; line-height: 1.6; }}
        </style>
    </head>
    <body>
        <h1>Angebot {offer['offer_number']}</h1>
        <div class="meta">
            Gültig bis: {offer['valid_until'].strftime('%d.%m.%Y')}
        </div>
        <div class="content">{offer['offer_text']}</div>
    </body>
    </html>
    """
    
    return {"html": html}


@router.get("/{offer_id}/signature-link")
async def get_signature_link(offer_id: str):
    """
    Get e-signature link (placeholder for DocuSign integration)
    """
    if offer_id not in _offers_db:
        raise HTTPException(status_code=404, detail="Angebot nicht gefunden")
    
    # TODO: Integrate with DocuSign
    return {
        "signature_link": f"https://docusign.example.com/sign/{offer_id}",
        "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
    }


@router.put("/{offer_id}/send")
async def send_offer(offer_id: str, customer_email: str, message: Optional[str] = None):
    """
    Send offer to customer via email
    """
    if offer_id not in _offers_db:
        raise HTTPException(status_code=404, detail="Angebot nicht gefunden")
    
    offer = _offers_db[offer_id]
    offer["status"] = "sent"
    _offers_db[offer_id] = offer
    
    # TODO: Send email
    
    return {
        "message": "Angebot gesendet",
        "sent_to": customer_email,
        "sent_at": datetime.utcnow().isoformat()
    }
