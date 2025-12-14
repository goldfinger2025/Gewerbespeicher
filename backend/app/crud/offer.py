"""
Offer CRUD Operations
Database operations for offers/quotes
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timedelta, date

from app.models.offer import Offer


async def get_offer_by_id(db: AsyncSession, offer_id: UUID) -> Optional[Offer]:
    """Get an offer by ID"""
    result = await db.execute(select(Offer).where(Offer.id == offer_id))
    return result.scalar_one_or_none()


async def get_offer_by_number(db: AsyncSession, offer_number: str) -> Optional[Offer]:
    """Get an offer by offer number"""
    result = await db.execute(select(Offer).where(Offer.offer_number == offer_number))
    return result.scalar_one_or_none()


async def get_offers_by_project(
    db: AsyncSession,
    project_id: UUID
) -> List[Offer]:
    """Get all offers for a project"""
    result = await db.execute(
        select(Offer)
        .where(Offer.project_id == project_id)
        .order_by(Offer.created_at.desc())
    )
    return list(result.scalars().all())


async def get_offers_by_user(
    db: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
) -> Tuple[List[Offer], int]:
    """Get paginated offers for a user (via projects) with total count"""
    from app.models.project import Project

    base_query = (
        select(Offer)
        .join(Project, Offer.project_id == Project.id)
        .where(Project.user_id == user_id)
    )

    if status:
        base_query = base_query.where(Offer.status == status)

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = base_query.order_by(Offer.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    offers = result.scalars().all()

    return list(offers), total


async def generate_offer_number(db: AsyncSession) -> str:
    """Generate a unique offer number"""
    year = datetime.now().year

    # Get the highest offer number for this year
    result = await db.execute(
        select(func.max(Offer.offer_number))
        .where(Offer.offer_number.like(f"EWS-{year}-%"))
    )
    last_number = result.scalar()

    if last_number:
        # Extract the counter and increment
        counter = int(last_number.split("-")[-1]) + 1
    else:
        counter = 1001  # Start from 1001

    return f"EWS-{year}-{counter:04d}"


async def create_offer(
    db: AsyncSession,
    simulation_id: UUID,
    project_id: UUID,
    offer_text: Optional[str] = None,
    validity_days: int = 30,
    **kwargs
) -> Offer:
    """Create a new offer"""
    offer_number = await generate_offer_number(db)
    valid_until = date.today() + timedelta(days=validity_days)

    offer = Offer(
        simulation_id=simulation_id,
        project_id=project_id,
        offer_number=offer_number,
        offer_text=offer_text,
        valid_until=valid_until,
        status="draft",
        **kwargs
    )
    db.add(offer)
    await db.flush()
    await db.refresh(offer)
    return offer


async def update_offer(
    db: AsyncSession,
    offer: Offer,
    **kwargs
) -> Offer:
    """Update offer fields"""
    for key, value in kwargs.items():
        if hasattr(offer, key) and value is not None:
            setattr(offer, key, value)
    await db.flush()
    await db.refresh(offer)
    return offer


async def mark_offer_sent(
    db: AsyncSession,
    offer: Offer
) -> Offer:
    """Mark offer as sent"""
    offer.status = "sent"
    await db.flush()
    await db.refresh(offer)
    return offer


async def mark_offer_signed(
    db: AsyncSession,
    offer: Offer,
    signer_name: str,
    signed_at: Optional[datetime] = None
) -> Offer:
    """Mark offer as signed"""
    offer.status = "signed"
    offer.is_signed = True
    offer.signed_at = signed_at or datetime.utcnow()
    offer.signer_name = signer_name
    await db.flush()
    await db.refresh(offer)
    return offer


async def update_offer_signature(
    db: AsyncSession,
    offer: Offer,
    signature_link: str,
    envelope_id: Optional[str] = None
) -> Offer:
    """Update offer with DocuSign signature link"""
    offer.signature_link = signature_link
    if envelope_id:
        # Store envelope_id in technical_specs JSON
        if offer.technical_specs is None:
            offer.technical_specs = {}
        offer.technical_specs["docusign_envelope_id"] = envelope_id
    offer.status = "sent"
    await db.flush()
    await db.refresh(offer)
    return offer


async def update_offer_crm(
    db: AsyncSession,
    offer: Offer,
    hubspot_deal_id: str
) -> Offer:
    """Update offer with HubSpot deal ID"""
    offer.hubspot_deal_id = hubspot_deal_id
    offer.crm_sync_status = "synced"
    await db.flush()
    await db.refresh(offer)
    return offer


async def update_offer_pdf(
    db: AsyncSession,
    offer: Offer,
    pdf_path: str
) -> Offer:
    """Update offer with PDF path"""
    offer.pdf_path = pdf_path
    offer.pdf_generated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(offer)
    return offer


async def delete_offer(db: AsyncSession, offer: Offer) -> None:
    """Delete an offer"""
    await db.delete(offer)
    await db.flush()
