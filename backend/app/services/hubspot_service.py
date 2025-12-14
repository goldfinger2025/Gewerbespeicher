"""
HubSpot CRM Integration Service
Synchronizes contacts, companies, and deals with HubSpot CRM
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
import aiohttp

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class HubSpotContact:
    """HubSpot Contact representation"""
    id: Optional[str] = None
    email: str = ""
    firstname: str = ""
    lastname: str = ""
    phone: str = ""
    company: str = ""


@dataclass
class HubSpotCompany:
    """HubSpot Company representation"""
    id: Optional[str] = None
    name: str = ""
    domain: str = ""
    city: str = ""
    address: str = ""
    postal_code: str = ""
    industry: str = "Energy & Utilities"


@dataclass
class HubSpotDeal:
    """HubSpot Deal representation"""
    id: Optional[str] = None
    dealname: str = ""
    amount: float = 0.0
    dealstage: str = "appointmentscheduled"
    pipeline: str = "default"
    closedate: Optional[str] = None
    offer_id: str = ""
    pv_power_kw: float = 0.0
    battery_capacity_kwh: float = 0.0


@dataclass
class SyncResult:
    """Result of a CRM sync operation"""
    success: bool
    entity_type: str  # contact, company, deal
    hubspot_id: Optional[str] = None
    action: str = ""  # created, updated, skipped
    error: Optional[str] = None


class HubSpotService:
    """
    HubSpot CRM Integration Service

    Provides bidirectional sync between Gewerbespeicher and HubSpot CRM.
    Supports contacts, companies, and deals.

    Environment Variables:
        HUBSPOT_API_KEY: Private app access token
        HUBSPOT_PORTAL_ID: HubSpot portal/account ID
    """

    BASE_URL = "https://api.hubapi.com"

    # HubSpot deal stages (customize based on your pipeline)
    DEAL_STAGES = {
        "new": "appointmentscheduled",
        "simulation_done": "qualifiedtobuy",
        "offer_sent": "presentationscheduled",
        "offer_viewed": "decisionmakerboughtin",
        "signed": "contractsent",
        "completed": "closedwon",
        "rejected": "closedlost"
    }

    # Custom property internal names (must be created in HubSpot first)
    CUSTOM_PROPERTIES = {
        "offer_id": "gewerbespeicher_offer_id",
        "project_id": "gewerbespeicher_project_id",
        "pv_power_kw": "pv_leistung_kwp",
        "battery_capacity_kwh": "speicher_kapazitaet_kwh",
        "annual_consumption_kwh": "jahresverbrauch_kwh",
        "autonomy_degree": "autarkiegrad_prozent",
        "payback_years": "amortisation_jahre"
    }

    def __init__(self):
        self.api_key = os.getenv("HUBSPOT_API_KEY", settings.HUBSPOT_API_KEY)
        self.portal_id = os.getenv("HUBSPOT_PORTAL_ID", "")

        self.is_configured = bool(self.api_key)

        if not self.is_configured:
            logger.warning("HubSpot not configured - missing API key")

    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    # ============ CONTACT OPERATIONS ============

    async def find_contact_by_email(self, email: str) -> Optional[HubSpotContact]:
        """
        Find a contact by email address

        Args:
            email: Email address to search for

        Returns:
            HubSpotContact if found, None otherwise
        """
        if not self.is_configured:
            return self._simulate_find_contact(email)

        try:
            async with aiohttp.ClientSession() as session:
                # Use search API
                search_body = {
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": email
                        }]
                    }],
                    "properties": ["email", "firstname", "lastname", "phone", "company"]
                }

                async with session.post(
                    f"{self.BASE_URL}/crm/v3/objects/contacts/search",
                    headers=self._get_headers(),
                    json=search_body
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        if results:
                            props = results[0].get("properties", {})
                            return HubSpotContact(
                                id=results[0].get("id"),
                                email=props.get("email", ""),
                                firstname=props.get("firstname", ""),
                                lastname=props.get("lastname", ""),
                                phone=props.get("phone", ""),
                                company=props.get("company", "")
                            )
                    return None

        except Exception as e:
            logger.error(f"Error finding contact: {e}")
            return None

    async def create_or_update_contact(
        self,
        email: str,
        firstname: str,
        lastname: str = "",
        phone: str = "",
        company: str = ""
    ) -> SyncResult:
        """
        Create or update a contact in HubSpot

        Args:
            email: Contact email (required)
            firstname: First name
            lastname: Last name
            phone: Phone number
            company: Company name

        Returns:
            SyncResult with operation outcome
        """
        if not self.is_configured:
            return self._simulate_create_contact(email, firstname)

        try:
            # Check if contact exists
            existing = await self.find_contact_by_email(email)

            properties = {
                "email": email,
                "firstname": firstname,
                "phone": phone,
                "company": company
            }

            if lastname:
                properties["lastname"] = lastname

            async with aiohttp.ClientSession() as session:
                if existing and existing.id:
                    # Update existing contact
                    async with session.patch(
                        f"{self.BASE_URL}/crm/v3/objects/contacts/{existing.id}",
                        headers=self._get_headers(),
                        json={"properties": properties}
                    ) as response:
                        if response.status == 200:
                            return SyncResult(
                                success=True,
                                entity_type="contact",
                                hubspot_id=existing.id,
                                action="updated"
                            )
                        else:
                            error = await response.text()
                            return SyncResult(
                                success=False,
                                entity_type="contact",
                                error=error
                            )
                else:
                    # Create new contact
                    async with session.post(
                        f"{self.BASE_URL}/crm/v3/objects/contacts",
                        headers=self._get_headers(),
                        json={"properties": properties}
                    ) as response:
                        if response.status == 201:
                            data = await response.json()
                            return SyncResult(
                                success=True,
                                entity_type="contact",
                                hubspot_id=data.get("id"),
                                action="created"
                            )
                        else:
                            error = await response.text()
                            return SyncResult(
                                success=False,
                                entity_type="contact",
                                error=error
                            )

        except Exception as e:
            logger.error(f"Error creating/updating contact: {e}")
            return SyncResult(
                success=False,
                entity_type="contact",
                error=str(e)
            )

    # ============ COMPANY OPERATIONS ============

    async def find_company_by_name(self, name: str) -> Optional[HubSpotCompany]:
        """Find a company by name"""
        if not self.is_configured:
            return None

        try:
            async with aiohttp.ClientSession() as session:
                search_body = {
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "name",
                            "operator": "EQ",
                            "value": name
                        }]
                    }],
                    "properties": ["name", "domain", "city", "address", "zip", "industry"]
                }

                async with session.post(
                    f"{self.BASE_URL}/crm/v3/objects/companies/search",
                    headers=self._get_headers(),
                    json=search_body
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        if results:
                            props = results[0].get("properties", {})
                            return HubSpotCompany(
                                id=results[0].get("id"),
                                name=props.get("name", ""),
                                domain=props.get("domain", ""),
                                city=props.get("city", ""),
                                address=props.get("address", ""),
                                postal_code=props.get("zip", "")
                            )
                    return None

        except Exception as e:
            logger.error(f"Error finding company: {e}")
            return None

    async def create_or_update_company(
        self,
        name: str,
        city: str = "",
        address: str = "",
        postal_code: str = "",
        domain: str = ""
    ) -> SyncResult:
        """Create or update a company in HubSpot"""
        if not self.is_configured:
            return self._simulate_create_company(name)

        try:
            existing = await self.find_company_by_name(name)

            properties = {
                "name": name,
                "city": city,
                "address": address,
                "zip": postal_code,
                "industry": "Energy & Utilities"
            }

            if domain:
                properties["domain"] = domain

            async with aiohttp.ClientSession() as session:
                if existing and existing.id:
                    async with session.patch(
                        f"{self.BASE_URL}/crm/v3/objects/companies/{existing.id}",
                        headers=self._get_headers(),
                        json={"properties": properties}
                    ) as response:
                        if response.status == 200:
                            return SyncResult(
                                success=True,
                                entity_type="company",
                                hubspot_id=existing.id,
                                action="updated"
                            )
                        else:
                            error = await response.text()
                            return SyncResult(
                                success=False,
                                entity_type="company",
                                error=error
                            )
                else:
                    async with session.post(
                        f"{self.BASE_URL}/crm/v3/objects/companies",
                        headers=self._get_headers(),
                        json={"properties": properties}
                    ) as response:
                        if response.status == 201:
                            data = await response.json()
                            return SyncResult(
                                success=True,
                                entity_type="company",
                                hubspot_id=data.get("id"),
                                action="created"
                            )
                        else:
                            error = await response.text()
                            return SyncResult(
                                success=False,
                                entity_type="company",
                                error=error
                            )

        except Exception as e:
            logger.error(f"Error creating/updating company: {e}")
            return SyncResult(
                success=False,
                entity_type="company",
                error=str(e)
            )

    # ============ DEAL OPERATIONS ============

    async def create_deal(
        self,
        dealname: str,
        amount: float,
        offer_id: str,
        contact_id: Optional[str] = None,
        company_id: Optional[str] = None,
        pv_power_kw: float = 0,
        battery_capacity_kwh: float = 0,
        autonomy_degree: float = 0,
        payback_years: float = 0,
        stage: str = "new"
    ) -> SyncResult:
        """
        Create a new deal in HubSpot

        Args:
            dealname: Name of the deal
            amount: Deal value in EUR
            offer_id: Internal offer ID
            contact_id: HubSpot contact ID to associate
            company_id: HubSpot company ID to associate
            pv_power_kw: PV system power
            battery_capacity_kwh: Battery capacity
            autonomy_degree: Calculated autonomy percentage
            payback_years: ROI payback period
            stage: Deal stage (maps to HubSpot pipeline stage)

        Returns:
            SyncResult with deal ID
        """
        if not self.is_configured:
            return self._simulate_create_deal(dealname, offer_id)

        try:
            # Map stage to HubSpot deal stage
            dealstage = self.DEAL_STAGES.get(stage, "appointmentscheduled")

            properties = {
                "dealname": dealname,
                "amount": str(amount),
                "dealstage": dealstage,
                "pipeline": "default",
                self.CUSTOM_PROPERTIES["offer_id"]: offer_id,
            }

            # Add custom properties if they exist in HubSpot
            if pv_power_kw:
                properties[self.CUSTOM_PROPERTIES["pv_power_kw"]] = str(pv_power_kw)
            if battery_capacity_kwh:
                properties[self.CUSTOM_PROPERTIES["battery_capacity_kwh"]] = str(battery_capacity_kwh)
            if autonomy_degree:
                properties[self.CUSTOM_PROPERTIES["autonomy_degree"]] = str(autonomy_degree)
            if payback_years:
                properties[self.CUSTOM_PROPERTIES["payback_years"]] = str(payback_years)

            async with aiohttp.ClientSession() as session:
                # Create deal
                async with session.post(
                    f"{self.BASE_URL}/crm/v3/objects/deals",
                    headers=self._get_headers(),
                    json={"properties": properties}
                ) as response:
                    if response.status == 201:
                        data = await response.json()
                        deal_id = data.get("id")

                        # Associate with contact and company
                        if contact_id:
                            await self._associate_deal(deal_id, "contacts", contact_id)
                        if company_id:
                            await self._associate_deal(deal_id, "companies", company_id)

                        return SyncResult(
                            success=True,
                            entity_type="deal",
                            hubspot_id=deal_id,
                            action="created"
                        )
                    else:
                        error = await response.text()
                        logger.error(f"Failed to create deal: {error}")
                        return SyncResult(
                            success=False,
                            entity_type="deal",
                            error=error
                        )

        except Exception as e:
            logger.error(f"Error creating deal: {e}")
            return SyncResult(
                success=False,
                entity_type="deal",
                error=str(e)
            )

    async def update_deal_stage(self, deal_id: str, stage: str) -> SyncResult:
        """
        Update deal stage in HubSpot

        Args:
            deal_id: HubSpot deal ID
            stage: New stage (internal name)

        Returns:
            SyncResult
        """
        if not self.is_configured:
            logger.info(f"[SIMULATION] Updating deal {deal_id} to stage {stage}")
            return SyncResult(
                success=True,
                entity_type="deal",
                hubspot_id=deal_id,
                action="updated"
            )

        try:
            dealstage = self.DEAL_STAGES.get(stage, stage)

            async with aiohttp.ClientSession() as session:
                async with session.patch(
                    f"{self.BASE_URL}/crm/v3/objects/deals/{deal_id}",
                    headers=self._get_headers(),
                    json={"properties": {"dealstage": dealstage}}
                ) as response:
                    if response.status == 200:
                        return SyncResult(
                            success=True,
                            entity_type="deal",
                            hubspot_id=deal_id,
                            action="updated"
                        )
                    else:
                        error = await response.text()
                        return SyncResult(
                            success=False,
                            entity_type="deal",
                            error=error
                        )

        except Exception as e:
            logger.error(f"Error updating deal stage: {e}")
            return SyncResult(
                success=False,
                entity_type="deal",
                error=str(e)
            )

    async def _associate_deal(
        self,
        deal_id: str,
        object_type: str,
        object_id: str
    ) -> bool:
        """Associate a deal with a contact or company"""
        try:
            async with aiohttp.ClientSession() as session:
                # Association type IDs
                # Deal to Contact: 3
                # Deal to Company: 5
                assoc_type = "3" if object_type == "contacts" else "5"

                async with session.put(
                    f"{self.BASE_URL}/crm/v3/objects/deals/{deal_id}/associations/{object_type}/{object_id}/{assoc_type}",
                    headers=self._get_headers()
                ) as response:
                    return response.status == 200

        except Exception as e:
            logger.error(f"Error associating deal: {e}")
            return False

    # ============ FULL PROJECT SYNC ============

    async def sync_project_to_crm(
        self,
        project: Dict[str, Any],
        simulation: Optional[Dict[str, Any]] = None,
        offer: Optional[Dict[str, Any]] = None
    ) -> Dict[str, SyncResult]:
        """
        Sync a complete project to HubSpot CRM

        Creates/updates contact, company, and deal in one operation.

        Args:
            project: Project data dict
            simulation: Optional simulation results
            offer: Optional offer data

        Returns:
            Dict with sync results for each entity type
        """
        results = {}

        # 1. Sync Contact
        customer_name = project.get("customer_name", "")
        name_parts = customer_name.split(" ", 1)
        firstname = name_parts[0]
        lastname = name_parts[1] if len(name_parts) > 1 else ""

        contact_result = await self.create_or_update_contact(
            email=project.get("customer_email", ""),
            firstname=firstname,
            lastname=lastname,
            phone=project.get("customer_phone", ""),
            company=project.get("customer_company", "")
        )
        results["contact"] = contact_result

        # 2. Sync Company (if provided)
        company_result = None
        if project.get("customer_company"):
            company_result = await self.create_or_update_company(
                name=project["customer_company"],
                city=project.get("city", ""),
                address=project.get("address", ""),
                postal_code=project.get("postal_code", "")
            )
            results["company"] = company_result

        # 3. Create Deal (if offer provided)
        if offer:
            # Calculate deal amount
            amount = offer.get("total_price", 0)
            if not amount and simulation:
                # Estimate from system size (rough calculation)
                pv_kw = project.get("pv_peak_power_kw", 0)
                battery_kwh = project.get("battery_capacity_kwh", 0)
                amount = (pv_kw * 1200) + (battery_kwh * 800)  # Rough EUR/kW and EUR/kWh

            deal_result = await self.create_deal(
                dealname=f"PV-Speicher {project.get('customer_company', customer_name)}",
                amount=amount,
                offer_id=offer.get("id", ""),
                contact_id=contact_result.hubspot_id if contact_result.success else None,
                company_id=company_result.hubspot_id if company_result and company_result.success else None,
                pv_power_kw=project.get("pv_peak_power_kw", 0),
                battery_capacity_kwh=project.get("battery_capacity_kwh", 0),
                autonomy_degree=simulation.get("autonomy_degree_percent", 0) if simulation else 0,
                payback_years=simulation.get("payback_period_years", 0) if simulation else 0,
                stage="offer_sent" if offer.get("status") == "sent" else "new"
            )
            results["deal"] = deal_result

        return results

    # ============ SIMULATION METHODS ============

    def _simulate_find_contact(self, email: str) -> Optional[HubSpotContact]:
        """Simulate finding a contact"""
        logger.info(f"[SIMULATION] Searching for contact: {email}")
        return None  # Simulate not found

    def _simulate_create_contact(self, email: str, firstname: str) -> SyncResult:
        """Simulate creating a contact"""
        fake_id = f"SIM-CONTACT-{hash(email) % 100000}"
        logger.info(f"[SIMULATION] Created contact {fake_id}: {firstname} <{email}>")
        return SyncResult(
            success=True,
            entity_type="contact",
            hubspot_id=fake_id,
            action="created"
        )

    def _simulate_create_company(self, name: str) -> SyncResult:
        """Simulate creating a company"""
        fake_id = f"SIM-COMPANY-{hash(name) % 100000}"
        logger.info(f"[SIMULATION] Created company {fake_id}: {name}")
        return SyncResult(
            success=True,
            entity_type="company",
            hubspot_id=fake_id,
            action="created"
        )

    def _simulate_create_deal(self, dealname: str, offer_id: str) -> SyncResult:
        """Simulate creating a deal"""
        fake_id = f"SIM-DEAL-{hash(offer_id) % 100000}"
        logger.info(f"[SIMULATION] Created deal {fake_id}: {dealname}")
        return SyncResult(
            success=True,
            entity_type="deal",
            hubspot_id=fake_id,
            action="created"
        )


# Singleton instance
_hubspot_service: Optional[HubSpotService] = None


def get_hubspot_service() -> HubSpotService:
    """Get or create HubSpot service instance"""
    global _hubspot_service
    if _hubspot_service is None:
        _hubspot_service = HubSpotService()
    return _hubspot_service
