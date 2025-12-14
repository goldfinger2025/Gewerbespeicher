"""
Integration Endpoints
Phase 3: Real-world integrations - DocuSign, HubSpot, Google Maps, PVGIS
"""

import base64
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from uuid import UUID
import io

from app.database import get_db
from app.models.user import User
from app.crud import project as project_crud
from app.crud import offer as offer_crud
from app.crud import simulation as simulation_crud
from app.api.deps import get_current_user

# Phase 3 Services
from app.services.docusign_service import get_docusign_service
from app.services.hubspot_service import get_hubspot_service
from app.services.google_maps_service import get_google_maps_service
from app.services.pvgis_service import get_pvgis_service
from app.services.pdf_service import pdf_service

logger = logging.getLogger(__name__)


router = APIRouter()


# ============ REQUEST/RESPONSE MODELS ============

class GeocodeRequest(BaseModel):
    address: str = Field(..., min_length=5, description="Full address to geocode")
    country: str = Field(default="DE", description="Country code")


class GeocodeResponse(BaseModel):
    latitude: float
    longitude: float
    formatted_address: str
    place_id: str
    city: str
    postal_code: str
    confidence: float


class SatelliteImageRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    zoom: int = Field(default=19, ge=1, le=21)
    width: int = Field(default=640, ge=100, le=640)
    height: int = Field(default=640, ge=100, le=640)


class SolarPotentialResponse(BaseModel):
    max_array_area_m2: float
    max_sunshine_hours_per_year: float
    panels_count: int
    yearly_energy_dc_kwh: float
    roof_segments: List[Dict[str, Any]]


class PVEstimationRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    pv_peak_kw: float = Field(..., gt=0, le=10000)
    tilt: Optional[float] = Field(default=None, ge=0, le=90)
    azimuth: Optional[float] = Field(default=None, ge=-180, le=180)


class PVEstimationResponse(BaseModel):
    pv_peak_kw: float
    annual_production_kwh: float
    monthly_production_kwh: List[float]
    optimal_tilt: float
    optimal_azimuth: float
    specific_yield_kwh_kwp: float


class SignatureRequest(BaseModel):
    offer_id: str
    signer_email: str = Field(..., min_length=5)
    signer_name: str = Field(..., min_length=2)


class SignatureResponse(BaseModel):
    envelope_id: str
    signing_url: str
    expires_at: datetime
    status: str


class CRMSyncRequest(BaseModel):
    project_id: str
    include_offer: bool = False


class CRMSyncResponse(BaseModel):
    success: bool
    contact_id: Optional[str] = None
    company_id: Optional[str] = None
    deal_id: Optional[str] = None
    errors: List[str] = []


class IntegrationStatusResponse(BaseModel):
    docusign: Dict[str, Any]
    hubspot: Dict[str, Any]
    google_maps: Dict[str, Any]
    pvgis: Dict[str, Any]


# ============ INTEGRATION STATUS ============

@router.get("/status", response_model=IntegrationStatusResponse)
async def get_integration_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get status of all Phase 3 integrations

    Returns configuration status and availability of each service.
    """
    docusign = get_docusign_service()
    hubspot = get_hubspot_service()
    google_maps = get_google_maps_service()

    return IntegrationStatusResponse(
        docusign={
            "configured": docusign.is_configured,
            "mode": "production" if docusign.is_production else "sandbox",
            "features": ["e-signature", "document-tracking", "webhooks"]
        },
        hubspot={
            "configured": hubspot.is_configured,
            "features": ["contacts", "companies", "deals", "sync"]
        },
        google_maps={
            "configured": google_maps.is_configured,
            "features": ["geocoding", "satellite-imagery", "solar-potential"]
        },
        pvgis={
            "configured": True,  # PVGIS is always available (public API)
            "features": ["tmy-data", "pv-estimation", "monthly-radiation"]
        }
    )


# ============ GOOGLE MAPS ENDPOINTS ============

@router.post("/geocode", response_model=GeocodeResponse)
async def geocode_address(
    request: GeocodeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Geocode an address to coordinates

    Uses Google Maps Geocoding API to convert addresses to lat/lng.
    Falls back to simulation mode if API key not configured.
    """
    maps_service = get_google_maps_service()

    result = await maps_service.geocode_address(
        address=request.address,
        country=request.country
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adresse konnte nicht gefunden werden"
        )

    return GeocodeResponse(
        latitude=result.latitude,
        longitude=result.longitude,
        formatted_address=result.formatted_address,
        place_id=result.place_id,
        city=result.city,
        postal_code=result.postal_code,
        confidence=result.confidence
    )


@router.get("/satellite-image")
async def get_satellite_image(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    zoom: int = Query(default=19, ge=1, le=21),
    width: int = Query(default=640, ge=100, le=640),
    height: int = Query(default=640, ge=100, le=640),
    current_user: User = Depends(get_current_user)
):
    """
    Get satellite image for a location

    Returns a satellite/aerial image from Google Maps Static API.
    """
    maps_service = get_google_maps_service()

    result = await maps_service.get_satellite_image(
        latitude=latitude,
        longitude=longitude,
        zoom=zoom,
        width=width,
        height=height
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Satellitenbild konnte nicht abgerufen werden"
        )

    return StreamingResponse(
        io.BytesIO(result.image_data),
        media_type=result.content_type,
        headers={
            "Content-Disposition": f"inline; filename=satellite_{latitude}_{longitude}.png"
        }
    )


@router.get("/solar-potential", response_model=SolarPotentialResponse)
async def get_solar_potential(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    current_user: User = Depends(get_current_user)
):
    """
    Get solar potential analysis for a building

    Uses Google Solar API where available, falls back to estimation.
    """
    maps_service = get_google_maps_service()

    result = await maps_service.get_solar_potential(
        latitude=latitude,
        longitude=longitude
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Solarpotenzial konnte nicht berechnet werden"
        )

    return SolarPotentialResponse(
        max_array_area_m2=result.max_array_area_m2,
        max_sunshine_hours_per_year=result.max_sunshine_hours_per_year,
        panels_count=result.panels_count,
        yearly_energy_dc_kwh=result.yearly_energy_dc_kwh,
        roof_segments=result.roof_segments
    )


# ============ PVGIS ENDPOINTS ============

@router.post("/pvgis/estimate", response_model=PVEstimationResponse)
async def estimate_pv_production(
    request: PVEstimationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Estimate annual PV production using PVGIS

    Returns detailed production estimates based on location and configuration.
    """
    pvgis = get_pvgis_service()

    result = await pvgis.estimate_pv_production(
        latitude=request.latitude,
        longitude=request.longitude,
        pv_peak_kw=request.pv_peak_kw,
        tilt=request.tilt,
        azimuth=request.azimuth
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PVGIS-Berechnung fehlgeschlagen"
        )

    return PVEstimationResponse(
        pv_peak_kw=result.pv_peak_kw,
        annual_production_kwh=result.annual_production_kwh,
        monthly_production_kwh=result.monthly_production_kwh,
        optimal_tilt=result.optimal_tilt,
        optimal_azimuth=result.optimal_azimuth,
        specific_yield_kwh_kwp=result.specific_yield_kwh_kwp
    )


@router.get("/pvgis/monthly")
async def get_monthly_radiation(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    current_user: User = Depends(get_current_user)
):
    """
    Get monthly radiation data from PVGIS

    Returns 12 months of solar radiation averages.
    """
    pvgis = get_pvgis_service()

    result = await pvgis.get_monthly_radiation(
        latitude=latitude,
        longitude=longitude
    )

    return {
        "location": {"latitude": latitude, "longitude": longitude},
        "monthly_data": [
            {
                "month": m.month,
                "ghi_kwh_m2": m.ghi_kwh_m2,
                "dni_kwh_m2": m.dni_kwh_m2,
                "dhi_kwh_m2": m.dhi_kwh_m2,
                "avg_temperature_c": m.avg_temperature,
                "sunshine_hours": m.sunshine_hours
            }
            for m in result
        ]
    }


@router.get("/pvgis/optimal")
async def get_optimal_configuration(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    pv_peak_kw: float = Query(..., gt=0, le=10000),
    current_user: User = Depends(get_current_user)
):
    """
    Get optimal PV configuration for a location

    Returns the optimal tilt and azimuth angles for maximum production.
    """
    pvgis = get_pvgis_service()

    result = await pvgis.get_optimal_configuration(
        latitude=latitude,
        longitude=longitude,
        pv_peak_kw=pv_peak_kw
    )

    return result


# ============ DOCUSIGN ENDPOINTS ============

@router.post("/docusign/send", response_model=SignatureResponse)
async def send_for_signature(
    request: SignatureRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send an offer for e-signature via DocuSign

    Creates a DocuSign envelope and returns the signing URL.
    """
    # Validate offer
    try:
        offer_uuid = UUID(request.offer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Angebots-ID"
        )

    offer = await offer_crud.get_offer_by_id(db=db, offer_id=offer_uuid)

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Angebot nicht gefunden"
        )

    # Verify ownership
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

    # Get simulation for PDF
    simulation = await simulation_crud.get_simulation_by_id(db=db, simulation_id=offer.simulation_id)

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation nicht gefunden"
        )

    # Generate PDF
    try:
        pdf_bytes = pdf_service.generate_offer_pdf(
            offer=offer,
            simulation=simulation,
            project=project
        )
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF konnte nicht generiert werden"
        )

    # Create DocuSign envelope
    docusign = get_docusign_service()

    result = await docusign.create_envelope(
        document_base64=pdf_base64,
        document_name=f"Angebot_{offer.offer_number}.pdf",
        signer_email=request.signer_email,
        signer_name=request.signer_name,
        offer_id=str(offer.id),
        subject=f"Angebot {offer.offer_number} - Bitte unterschreiben",
        email_body=f"Sehr geehrte/r {request.signer_name},\n\nbitte unterschreiben Sie das beigefügte Angebot."
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DocuSign-Signatur konnte nicht erstellt werden"
        )

    # Update offer with signature info
    await offer_crud.update_offer_signature(
        db=db,
        offer=offer,
        signature_link=result.signing_url,
        envelope_id=result.envelope_id
    )

    return SignatureResponse(
        envelope_id=result.envelope_id,
        signing_url=result.signing_url,
        expires_at=result.expires_at,
        status=result.status
    )


@router.get("/docusign/status/{envelope_id}")
async def get_signature_status(
    envelope_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get status of a DocuSign envelope

    Returns current signing status and signer information.
    """
    docusign = get_docusign_service()

    result = await docusign.get_envelope_status(envelope_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Envelope nicht gefunden"
        )

    return {
        "envelope_id": result.envelope_id,
        "status": result.status,
        "signed_at": result.signed_at.isoformat() if result.signed_at else None,
        "signer_name": result.signer_name,
        "signer_email": result.signer_email
    }


@router.post("/docusign/webhook")
async def docusign_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    DocuSign Connect webhook endpoint

    Receives signature status updates from DocuSign.
    """
    docusign = get_docusign_service()

    # Get raw body for signature verification
    body = await request.body()
    signature = request.headers.get("X-DocuSign-Signature-1", "")

    # Verify webhook signature
    if not docusign.verify_webhook_signature(body, signature):
        logger.warning("Invalid DocuSign webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )

    # Parse event
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON"
        )

    event = docusign.parse_webhook_event(data)

    if not event:
        return {"status": "ignored"}

    # Update offer if we have an offer_id
    if event.get("offer_id"):
        try:
            offer_uuid = UUID(event["offer_id"])
            offer = await offer_crud.get_offer_by_id(db=db, offer_id=offer_uuid)

            if offer:
                # Update based on status
                if event["status"] == "completed":
                    await offer_crud.mark_offer_signed(
                        db=db,
                        offer=offer,
                        signer_name=event.get("signer_name", ""),
                        signed_at=datetime.fromisoformat(event["signed_at"].replace("Z", "+00:00")) if event.get("signed_at") else datetime.utcnow()
                    )
                    logger.info(f"Offer {offer.offer_number} signed via DocuSign")

        except Exception as e:
            logger.error(f"Error processing DocuSign webhook: {e}")

    return {"status": "processed"}


# ============ HUBSPOT ENDPOINTS ============

@router.post("/hubspot/sync", response_model=CRMSyncResponse)
async def sync_to_hubspot(
    request: CRMSyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync a project to HubSpot CRM

    Creates/updates contact, company, and optionally deal in HubSpot.
    """
    # Validate project
    try:
        project_uuid = UUID(request.project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Projekt-ID"
        )

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
        "customer_email": project.customer_email,
        "customer_phone": project.customer_phone,
        "customer_company": project.customer_company,
        "address": project.address,
        "city": project.city,
        "postal_code": project.postal_code,
        "pv_peak_power_kw": project.pv_peak_power_kw,
        "battery_capacity_kwh": project.battery_capacity_kwh,
    }

    # Get simulation and offer if requested
    simulation_data = None
    offer_data = None

    if request.include_offer:
        # Get latest offer for project
        offers = await offer_crud.get_offers_by_project(db=db, project_id=project_uuid)
        if offers:
            latest_offer = offers[0]
            offer_data = {
                "id": str(latest_offer.id),
                "offer_number": latest_offer.offer_number,
                "status": latest_offer.status,
            }

            # Get simulation
            simulation = await simulation_crud.get_simulation_by_id(
                db=db, simulation_id=latest_offer.simulation_id
            )
            if simulation:
                simulation_data = {
                    "autonomy_degree_percent": simulation.autonomy_degree_percent,
                    "payback_period_years": simulation.payback_period_years,
                }

    # Sync to HubSpot
    hubspot = get_hubspot_service()

    results = await hubspot.sync_project_to_crm(
        project=project_data,
        simulation=simulation_data,
        offer=offer_data
    )

    # Collect results
    errors = []
    contact_id = None
    company_id = None
    deal_id = None

    if "contact" in results:
        if results["contact"].success:
            contact_id = results["contact"].hubspot_id
        else:
            errors.append(f"Contact: {results['contact'].error}")

    if "company" in results:
        if results["company"].success:
            company_id = results["company"].hubspot_id
        else:
            errors.append(f"Company: {results['company'].error}")

    if "deal" in results:
        if results["deal"].success:
            deal_id = results["deal"].hubspot_id

            # Update offer with HubSpot deal ID
            if offer_data and offers:
                await offer_crud.update_offer_crm(
                    db=db,
                    offer=offers[0],
                    hubspot_deal_id=deal_id
                )
        else:
            errors.append(f"Deal: {results['deal'].error}")

    return CRMSyncResponse(
        success=len(errors) == 0,
        contact_id=contact_id,
        company_id=company_id,
        deal_id=deal_id,
        errors=errors
    )


@router.put("/hubspot/deal/{deal_id}/stage")
async def update_hubspot_deal_stage(
    deal_id: str,
    stage: str = Query(..., description="New deal stage"),
    current_user: User = Depends(get_current_user)
):
    """
    Update deal stage in HubSpot

    Valid stages: new, simulation_done, offer_sent, offer_viewed, signed, completed, rejected
    """
    hubspot = get_hubspot_service()

    result = await hubspot.update_deal_stage(deal_id, stage)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"HubSpot update failed: {result.error}"
        )

    return {
        "success": True,
        "deal_id": deal_id,
        "new_stage": stage
    }


# ============ PROJECT GEOCODING ============

@router.post("/projects/{project_id}/geocode")
async def geocode_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Geocode a project's address and update coordinates

    Uses Google Maps to convert the project address to lat/lng.
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige Projekt-ID"
        )

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

    # Build full address
    address_parts = [project.address]
    if project.postal_code:
        address_parts.append(project.postal_code)
    if project.city:
        address_parts.append(project.city)
    address_parts.append("Deutschland")

    full_address = ", ".join(filter(None, address_parts))

    # Geocode
    maps_service = get_google_maps_service()
    location = await maps_service.geocode_address(full_address)

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adresse konnte nicht geocodiert werden"
        )

    # Update project
    await project_crud.update_project_coordinates(
        db=db,
        project=project,
        latitude=location.latitude,
        longitude=location.longitude
    )

    return {
        "success": True,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "formatted_address": location.formatted_address,
        "confidence": location.confidence
    }
