"""
Offer Endpoints
Generate and manage quotes/offers with Claude AI integration
"""

import os
import logging
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.offer import Offer
from app.crud import project as project_crud
from app.crud import simulation as simulation_crud
from app.crud import offer as offer_crud
from app.api.deps import get_current_user
from app.services.claude_service import get_claude_service
from app.services.pdf_service import pdf_service
from app.services.email_service import email_service

logger = logging.getLogger(__name__)


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

    class Config:
        from_attributes = True


class OfferListResponse(BaseModel):
    total: int
    items: List[OfferResponse]


class SendOfferRequest(BaseModel):
    customer_email: str
    message: Optional[str] = None


# ============ HELPER FUNCTIONS ============

def offer_to_response(offer: Offer) -> OfferResponse:
    """Convert SQLAlchemy Offer model to Pydantic response"""
    return OfferResponse(
        id=str(offer.id),
        simulation_id=str(offer.simulation_id),
        project_id=str(offer.project_id),
        offer_number=offer.offer_number,
        offer_text=offer.offer_text,
        pdf_path=offer.pdf_path,
        is_signed=offer.is_signed,
        valid_until=datetime.combine(offer.valid_until, datetime.min.time()) if offer.valid_until else datetime.utcnow(),
        status=offer.status,
        created_at=offer.created_at,
    )


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


# ============ ENDPOINTS ============

@router.post("", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
async def create_offer(
    request: OfferCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new offer from simulation results
    Uses Claude AI to generate professional offer text
    """
    # Validate simulation_id
    try:
        simulation_uuid = UUID(request.simulation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Simulations-ID"
        )

    # Get simulation
    simulation = await simulation_crud.get_simulation_by_id(db=db, simulation_id=simulation_uuid)

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation nicht gefunden"
        )

    # Get project and verify ownership
    project = await project_crud.get_project_by_id(
        db=db,
        project_id=simulation.project_id,
        user_id=current_user.id
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projekt nicht gefunden"
        )

    # Prepare simulation results for Claude
    results = {
        "pv_generation_kwh": simulation.pv_generation_kwh or 0,
        "self_consumption_kwh": simulation.self_consumed_kwh or 0,
        "grid_import_kwh": simulation.consumed_from_grid_kwh or 0,
        "grid_export_kwh": simulation.fed_to_grid_kwh or 0,
        "autonomy_degree_percent": simulation.autonomy_degree_percent or 0,
        "self_consumption_ratio_percent": simulation.self_consumption_ratio_percent or 0,
        "annual_savings_eur": simulation.annual_savings_eur or 0,
        "payback_period_years": simulation.payback_period_years or 0,
        "battery_cycles": simulation.battery_discharge_cycles or 0,
    }

    # Prepare project data
    project_data = {
        "customer_name": project.customer_name,
        "customer_company": project.customer_company,
        "address": project.address,
        "city": project.city,
        "pv_peak_power_kw": project.pv_peak_power_kw,
        "battery_capacity_kwh": project.battery_capacity_kwh,
        "annual_consumption_kwh": project.annual_consumption_kwh,
        "electricity_price_eur_kwh": project.electricity_price_eur_kwh,
    }

    # Use Claude to generate offer text
    claude = get_claude_service()
    try:
        offer_text = await claude.generate_offer_text(
            project=project_data,
            simulation=results,
            components=None
        )
    except Exception:
        # Fallback to basic text if Claude fails
        offer_text = _generate_fallback_offer_text(project_data, results)

    # Create offer in database
    offer = await offer_crud.create_offer(
        db=db,
        simulation_id=simulation.id,
        project_id=project.id,
        offer_text=offer_text,
    )

    # Generate PDF if requested
    if request.generate_pdf:
        try:
            # Create PDF directory if needed
            pdf_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "pdfs")
            pdf_dir = os.path.abspath(pdf_dir)
            os.makedirs(pdf_dir, exist_ok=True)

            pdf_filename = f"Angebot_{offer.offer_number}.pdf"
            pdf_path = os.path.join(pdf_dir, pdf_filename)

            # Generate PDF
            pdf_service.generate_offer_pdf(
                offer=offer,
                simulation=simulation,
                project=project,
                output_path=pdf_path
            )

            # Update offer with PDF path
            await offer_crud.update_offer_pdf(
                db=db,
                offer=offer,
                pdf_path=pdf_filename
            )
            logger.info(f"PDF generated for offer {offer.offer_number}")
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            # Continue without PDF - not critical

    return offer_to_response(offer)


@router.get("", response_model=OfferListResponse)
async def list_offers(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all offers for current user
    """
    offers, total = await offer_crud.get_offers_by_user(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        status=status,
    )

    return OfferListResponse(
        total=total,
        items=[offer_to_response(o) for o in offers]
    )


@router.get("/{offer_id}", response_model=OfferResponse)
async def get_offer(
    offer_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get offer details
    """
    try:
        uuid_id = UUID(offer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Angebots-ID"
        )

    offer = await offer_crud.get_offer_by_id(db=db, offer_id=uuid_id)

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Angebot nicht gefunden"
        )

    # Verify user owns the project
    project = await project_crud.get_project_by_id(
        db=db,
        project_id=offer.project_id,
        user_id=current_user.id
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Angebot nicht gefunden"
        )

    return offer_to_response(offer)


@router.get("/{offer_id}/preview", response_class=HTMLResponse)
async def get_offer_preview(
    offer_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get HTML preview of offer
    """
    try:
        uuid_id = UUID(offer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Angebots-ID"
        )

    offer = await offer_crud.get_offer_by_id(db=db, offer_id=uuid_id)

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Angebot nicht gefunden"
        )

    # Verify user owns the project
    project = await project_crud.get_project_by_id(
        db=db,
        project_id=offer.project_id,
        user_id=current_user.id
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Angebot nicht gefunden"
        )

    # Format valid_until date
    valid_until_str = offer.valid_until.strftime('%d.%m.%Y') if offer.valid_until else "N/A"

    # Return HTML preview
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Angebot {offer.offer_number}</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; }}
            h1 {{ color: #1e40af; }}
            .meta {{ color: #64748b; margin-bottom: 20px; }}
            .content {{ white-space: pre-wrap; line-height: 1.6; }}
        </style>
    </head>
    <body>
        <h1>Angebot {offer.offer_number}</h1>
        <div class="meta">
            Gültig bis: {valid_until_str}
        </div>
        <div class="content">{offer.offer_text or ''}</div>
    </body>
    </html>
    """

    return HTMLResponse(content=html)


@router.get("/{offer_id}/signature-link")
async def get_signature_link(
    offer_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get e-signature link (placeholder for DocuSign integration)
    """
    try:
        uuid_id = UUID(offer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Angebots-ID"
        )

    offer = await offer_crud.get_offer_by_id(db=db, offer_id=uuid_id)

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Angebot nicht gefunden"
        )

    # Verify user owns the project
    project = await project_crud.get_project_by_id(
        db=db,
        project_id=offer.project_id,
        user_id=current_user.id
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Angebot nicht gefunden"
        )

    # TODO: Integrate with DocuSign
    return {
        "signature_link": f"https://docusign.example.com/sign/{offer_id}",
        "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
    }


@router.put("/{offer_id}/send")
async def send_offer(
    offer_id: str,
    request: SendOfferRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send offer to customer via email
    """
    try:
        uuid_id = UUID(offer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Angebots-ID"
        )

    offer = await offer_crud.get_offer_by_id(db=db, offer_id=uuid_id)

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Angebot nicht gefunden"
        )

    # Verify user owns the project
    project = await project_crud.get_project_by_id(
        db=db,
        project_id=offer.project_id,
        user_id=current_user.id
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Angebot nicht gefunden"
        )

    # Mark as sent
    await offer_crud.mark_offer_sent(db=db, offer=offer)

    # Send email (PDF attachment can be added later)
    email_result = await email_service.send_offer_email_simulated(
        to_email=request.customer_email,
        customer_name=project.customer_name,
        offer_number=offer.offer_number,
        offer_text=offer.offer_text or "",
        valid_until=datetime.combine(offer.valid_until, datetime.min.time()) if offer.valid_until else None,
        custom_message=request.message,
    )

    return {
        "message": "Angebot gesendet" if email_result["success"] else "Angebot als gesendet markiert",
        "sent_to": request.customer_email,
        "sent_at": datetime.utcnow().isoformat(),
        "email_status": email_result
    }


@router.get("/project/{project_id}", response_model=List[OfferResponse])
async def get_project_offers(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all offers for a project
    """
    try:
        uuid_id = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Projekt-ID"
        )

    # Verify user owns the project
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

    offers = await offer_crud.get_offers_by_project(db=db, project_id=uuid_id)

    return [offer_to_response(o) for o in offers]


@router.get("/{offer_id}/pdf")
async def download_offer_pdf(
    offer_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download offer as PDF
    """
    try:
        uuid_id = UUID(offer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Angebots-ID"
        )

    offer = await offer_crud.get_offer_by_id(db=db, offer_id=uuid_id)

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Angebot nicht gefunden"
        )

    # Verify user owns the project
    project = await project_crud.get_project_by_id(
        db=db,
        project_id=offer.project_id,
        user_id=current_user.id
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Angebot nicht gefunden"
        )

    # Check if PDF exists
    if not offer.pdf_path:
        # Generate PDF on-demand
        simulation = await simulation_crud.get_simulation_by_id(db=db, simulation_id=offer.simulation_id)

        if not simulation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Simulation nicht gefunden"
            )

        try:
            pdf_bytes = pdf_service.generate_offer_pdf(
                offer=offer,
                simulation=simulation,
                project=project
            )
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF konnte nicht generiert werden"
            )
    else:
        # Load existing PDF
        pdf_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "pdfs")
        pdf_dir = os.path.abspath(pdf_dir)
        pdf_full_path = os.path.join(pdf_dir, offer.pdf_path)

        if not os.path.exists(pdf_full_path):
            # PDF file missing, regenerate
            simulation = await simulation_crud.get_simulation_by_id(db=db, simulation_id=offer.simulation_id)

            if not simulation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Simulation nicht gefunden"
                )

            try:
                pdf_bytes = pdf_service.generate_offer_pdf(
                    offer=offer,
                    simulation=simulation,
                    project=project
                )
            except Exception as e:
                logger.error(f"Failed to generate PDF: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="PDF konnte nicht generiert werden"
                )
        else:
            with open(pdf_full_path, 'rb') as f:
                pdf_bytes = f.read()

    filename = f"Angebot_{offer.offer_number}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/{offer_id}/regenerate-pdf")
async def regenerate_offer_pdf(
    offer_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate PDF for an existing offer
    """
    try:
        uuid_id = UUID(offer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Angebots-ID"
        )

    offer = await offer_crud.get_offer_by_id(db=db, offer_id=uuid_id)

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Angebot nicht gefunden"
        )

    # Verify user owns the project
    project = await project_crud.get_project_by_id(
        db=db,
        project_id=offer.project_id,
        user_id=current_user.id
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Angebot nicht gefunden"
        )

    simulation = await simulation_crud.get_simulation_by_id(db=db, simulation_id=offer.simulation_id)

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation nicht gefunden"
        )

    try:
        # Create PDF directory if needed
        pdf_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "pdfs")
        pdf_dir = os.path.abspath(pdf_dir)
        os.makedirs(pdf_dir, exist_ok=True)

        pdf_filename = f"Angebot_{offer.offer_number}.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)

        # Generate PDF
        pdf_service.generate_offer_pdf(
            offer=offer,
            simulation=simulation,
            project=project,
            output_path=pdf_path
        )

        # Update offer with PDF path
        await offer_crud.update_offer_pdf(
            db=db,
            offer=offer,
            pdf_path=pdf_filename
        )

        return {
            "message": "PDF erfolgreich neu generiert",
            "pdf_path": pdf_filename
        }
    except Exception as e:
        logger.error(f"Failed to regenerate PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF konnte nicht generiert werden: {str(e)}"
        )
