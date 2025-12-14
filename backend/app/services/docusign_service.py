"""
DocuSign E-Signature Service
Integration for electronic signatures on offers/quotes
"""

import os
import logging
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
import aiohttp
import base64

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SignatureRequest:
    """Data class for signature request"""
    envelope_id: str
    signing_url: str
    expires_at: datetime
    status: str


@dataclass
class SignatureStatus:
    """Data class for signature status"""
    envelope_id: str
    status: str  # created, sent, delivered, signed, completed, declined, voided
    signed_at: Optional[datetime] = None
    signer_name: Optional[str] = None
    signer_email: Optional[str] = None


class DocuSignService:
    """
    DocuSign API Integration Service

    Provides e-signature capabilities for offers and contracts.
    Uses DocuSign eSignature REST API v2.1

    Environment Variables:
        DOCUSIGN_API_KEY: Integration key (client ID)
        DOCUSIGN_ACCOUNT_ID: DocuSign account ID
        DOCUSIGN_USER_ID: User ID for JWT authentication
        DOCUSIGN_PRIVATE_KEY: RSA private key for JWT auth
        DOCUSIGN_BASE_URL: API base URL (demo or production)
    """

    # DocuSign API endpoints
    DEMO_BASE_URL = "https://demo.docusign.net/restapi"
    PROD_BASE_URL = "https://eu.docusign.net/restapi"  # EU datacenter
    DEMO_AUTH_URL = "https://account-d.docusign.com"
    PROD_AUTH_URL = "https://account.docusign.com"

    def __init__(self):
        self.api_key = os.getenv("DOCUSIGN_API_KEY", settings.DOCUSIGN_API_KEY)
        self.account_id = os.getenv("DOCUSIGN_ACCOUNT_ID", "")
        self.user_id = os.getenv("DOCUSIGN_USER_ID", "")
        self.private_key = os.getenv("DOCUSIGN_PRIVATE_KEY", "")
        self.webhook_secret = os.getenv("DOCUSIGN_WEBHOOK_SECRET", "")

        # Use demo environment if no production config
        self.is_production = os.getenv("DOCUSIGN_PRODUCTION", "false").lower() == "true"
        self.base_url = self.PROD_BASE_URL if self.is_production else self.DEMO_BASE_URL
        self.auth_url = self.PROD_AUTH_URL if self.is_production else self.DEMO_AUTH_URL

        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

        # Check if properly configured
        self.is_configured = bool(self.api_key and self.account_id)

    async def _get_access_token(self) -> Optional[str]:
        """
        Get OAuth access token using JWT Grant flow

        DocuSign requires JWT authentication for server-to-server integration.
        The JWT is signed with RSA private key and exchanged for an access token.
        """
        if not self.is_configured:
            logger.warning("DocuSign not configured - missing API key or account ID")
            return None

        # Return cached token if still valid
        if self._access_token and self._token_expires_at:
            if datetime.utcnow() < self._token_expires_at - timedelta(minutes=5):
                return self._access_token

        # For demo/development without full JWT setup, use simulation mode
        if not self.private_key:
            logger.info("DocuSign running in simulation mode (no private key)")
            return "simulated_token"

        try:
            # Build JWT assertion
            import jwt

            now = datetime.utcnow()
            payload = {
                "iss": self.api_key,
                "sub": self.user_id,
                "aud": self.auth_url.replace("https://", ""),
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(hours=1)).timestamp()),
                "scope": "signature impersonation"
            }

            assertion = jwt.encode(
                payload,
                self.private_key,
                algorithm="RS256"
            )

            # Exchange JWT for access token
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.auth_url}/oauth/token",
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": assertion
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._access_token = data["access_token"]
                        self._token_expires_at = datetime.utcnow() + timedelta(
                            seconds=data.get("expires_in", 3600)
                        )
                        return self._access_token
                    else:
                        error = await response.text()
                        logger.error(f"DocuSign auth failed: {error}")
                        return None

        except ImportError:
            logger.warning("PyJWT not installed - DocuSign running in simulation mode")
            return "simulated_token"
        except Exception as e:
            logger.error(f"DocuSign authentication error: {e}")
            return None

    async def create_envelope(
        self,
        document_base64: str,
        document_name: str,
        signer_email: str,
        signer_name: str,
        offer_id: str,
        subject: str = "Angebot zur Unterschrift",
        email_body: str = "Bitte unterschreiben Sie das beigefügte Angebot."
    ) -> Optional[SignatureRequest]:
        """
        Create a DocuSign envelope for signing

        Args:
            document_base64: Base64 encoded PDF document
            document_name: Name of the document
            signer_email: Email address of the signer
            signer_name: Name of the signer
            offer_id: Internal offer ID for tracking
            subject: Email subject line
            email_body: Email body text

        Returns:
            SignatureRequest with envelope ID and signing URL
        """
        token = await self._get_access_token()

        if not token:
            logger.error("Cannot create envelope - no access token")
            return None

        # Simulation mode for development
        if token == "simulated_token":
            return self._simulate_create_envelope(offer_id, signer_email, signer_name)

        try:
            envelope_definition = {
                "emailSubject": subject,
                "emailBlurb": email_body,
                "documents": [{
                    "documentBase64": document_base64,
                    "name": document_name,
                    "fileExtension": "pdf",
                    "documentId": "1"
                }],
                "recipients": {
                    "signers": [{
                        "email": signer_email,
                        "name": signer_name,
                        "recipientId": "1",
                        "routingOrder": "1",
                        "tabs": {
                            "signHereTabs": [{
                                "documentId": "1",
                                "pageNumber": "1",
                                "anchorString": "/sig1/",
                                "anchorXOffset": "0",
                                "anchorYOffset": "0"
                            }],
                            "dateSignedTabs": [{
                                "documentId": "1",
                                "pageNumber": "1",
                                "anchorString": "/date1/",
                                "anchorXOffset": "0",
                                "anchorYOffset": "0"
                            }]
                        }
                    }]
                },
                "status": "sent",  # Send immediately
                "customFields": {
                    "textCustomFields": [{
                        "name": "offer_id",
                        "value": offer_id
                    }]
                }
            }

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }

                async with session.post(
                    f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes",
                    headers=headers,
                    json=envelope_definition
                ) as response:
                    if response.status in (200, 201):
                        data = await response.json()
                        envelope_id = data["envelopeId"]

                        # Get signing URL
                        signing_url = await self._get_recipient_view(
                            envelope_id,
                            signer_email,
                            signer_name,
                            offer_id
                        )

                        return SignatureRequest(
                            envelope_id=envelope_id,
                            signing_url=signing_url or "",
                            expires_at=datetime.utcnow() + timedelta(days=7),
                            status="sent"
                        )
                    else:
                        error = await response.text()
                        logger.error(f"Failed to create envelope: {error}")
                        return None

        except Exception as e:
            logger.error(f"Error creating DocuSign envelope: {e}")
            return None

    async def _get_recipient_view(
        self,
        envelope_id: str,
        signer_email: str,
        signer_name: str,
        offer_id: str
    ) -> Optional[str]:
        """Get embedded signing URL for recipient"""
        token = await self._get_access_token()

        if not token or token == "simulated_token":
            return None

        try:
            recipient_view_request = {
                "returnUrl": f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/dashboard/offers/{offer_id}/signed",
                "authenticationMethod": "email",
                "email": signer_email,
                "userName": signer_name,
                "clientUserId": offer_id  # For embedded signing
            }

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }

                async with session.post(
                    f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}/views/recipient",
                    headers=headers,
                    json=recipient_view_request
                ) as response:
                    if response.status == 201:
                        data = await response.json()
                        return data.get("url")
                    else:
                        error = await response.text()
                        logger.error(f"Failed to get recipient view: {error}")
                        return None

        except Exception as e:
            logger.error(f"Error getting recipient view: {e}")
            return None

    async def get_envelope_status(self, envelope_id: str) -> Optional[SignatureStatus]:
        """
        Get current status of an envelope

        Args:
            envelope_id: DocuSign envelope ID

        Returns:
            SignatureStatus with current state
        """
        token = await self._get_access_token()

        if not token:
            return None

        # Simulation mode
        if token == "simulated_token":
            return self._simulate_get_status(envelope_id)

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {token}"}

                async with session.get(
                    f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()

                        signed_at = None
                        if data.get("completedDateTime"):
                            signed_at = datetime.fromisoformat(
                                data["completedDateTime"].replace("Z", "+00:00")
                            )

                        return SignatureStatus(
                            envelope_id=envelope_id,
                            status=data.get("status", "unknown"),
                            signed_at=signed_at,
                            signer_name=None,  # Would need to fetch recipients
                            signer_email=None
                        )
                    else:
                        logger.error(f"Failed to get envelope status: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Error getting envelope status: {e}")
            return None

    async def void_envelope(self, envelope_id: str, reason: str = "Angebot zurückgezogen") -> bool:
        """
        Void/cancel an envelope

        Args:
            envelope_id: DocuSign envelope ID
            reason: Reason for voiding

        Returns:
            True if successful
        """
        token = await self._get_access_token()

        if not token:
            return False

        if token == "simulated_token":
            logger.info(f"[SIMULATION] Voiding envelope {envelope_id}: {reason}")
            return True

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }

                async with session.put(
                    f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}",
                    headers=headers,
                    json={"status": "voided", "voidedReason": reason}
                ) as response:
                    return response.status == 200

        except Exception as e:
            logger.error(f"Error voiding envelope: {e}")
            return False

    async def download_signed_document(self, envelope_id: str) -> Optional[bytes]:
        """
        Download the signed document

        Args:
            envelope_id: DocuSign envelope ID

        Returns:
            PDF bytes of signed document
        """
        token = await self._get_access_token()

        if not token:
            return None

        if token == "simulated_token":
            logger.info(f"[SIMULATION] Would download signed document for {envelope_id}")
            return None

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {token}"}

                async with session.get(
                    f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}/documents/combined",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Failed to download document: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Error downloading document: {e}")
            return None

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify DocuSign Connect webhook signature

        Args:
            payload: Raw request body
            signature: X-DocuSign-Signature-1 header value

        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            logger.warning("No webhook secret configured - skipping verification")
            return True

        try:
            expected = base64.b64encode(
                hmac.new(
                    self.webhook_secret.encode(),
                    payload,
                    hashlib.sha256
                ).digest()
            ).decode()

            return hmac.compare_digest(expected, signature)

        except Exception as e:
            logger.error(f"Webhook verification error: {e}")
            return False

    def parse_webhook_event(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse DocuSign Connect webhook event

        Args:
            data: Webhook JSON payload

        Returns:
            Parsed event data with offer_id and status
        """
        try:
            envelope_id = data.get("envelopeId")
            status = data.get("status")

            # Extract custom field (offer_id)
            offer_id = None
            custom_fields = data.get("customFields", {}).get("textCustomFields", [])
            for field in custom_fields:
                if field.get("name") == "offer_id":
                    offer_id = field.get("value")
                    break

            # Get signer info
            signer_name = None
            signer_email = None
            recipients = data.get("recipients", {}).get("signers", [])
            if recipients:
                signer_name = recipients[0].get("name")
                signer_email = recipients[0].get("email")

            return {
                "envelope_id": envelope_id,
                "offer_id": offer_id,
                "status": status,
                "signer_name": signer_name,
                "signer_email": signer_email,
                "signed_at": data.get("completedDateTime"),
                "event_type": data.get("event", "unknown")
            }

        except Exception as e:
            logger.error(f"Error parsing webhook: {e}")
            return None

    # ============ SIMULATION METHODS ============

    def _simulate_create_envelope(
        self,
        offer_id: str,
        signer_email: str,
        signer_name: str
    ) -> SignatureRequest:
        """Create simulated envelope for development"""
        envelope_id = f"SIM-{offer_id[:8]}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        logger.info(f"[SIMULATION] Created envelope {envelope_id} for {signer_name} <{signer_email}>")

        return SignatureRequest(
            envelope_id=envelope_id,
            signing_url=f"https://demo.docusign.net/Signing/Simulated?envelopeId={envelope_id}",
            expires_at=datetime.utcnow() + timedelta(days=7),
            status="sent"
        )

    def _simulate_get_status(self, envelope_id: str) -> SignatureStatus:
        """Get simulated envelope status"""
        # In simulation, envelopes are always "sent"
        return SignatureStatus(
            envelope_id=envelope_id,
            status="sent",
            signed_at=None,
            signer_name=None,
            signer_email=None
        )


# Singleton instance
_docusign_service: Optional[DocuSignService] = None


def get_docusign_service() -> DocuSignService:
    """Get or create DocuSign service instance"""
    global _docusign_service
    if _docusign_service is None:
        _docusign_service = DocuSignService()
    return _docusign_service
