"""
Email Service
Handles sending emails for offer notifications
"""

import logging
import smtplib
import html
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


def sanitize_for_html(text: str) -> str:
    """Sanitize text for safe HTML embedding to prevent XSS"""
    if not text:
        return ""
    return html.escape(str(text))


class EmailService:
    """Service for sending emails"""

    def __init__(self):
        # Email configuration (from environment variables)
        self.smtp_host = getattr(settings, 'SMTP_HOST', '')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_user = getattr(settings, 'SMTP_USER', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.from_email = getattr(settings, 'FROM_EMAIL', 'noreply@ews-gmbh.de')
        self.from_name = getattr(settings, 'FROM_NAME', 'EWS GmbH - Gewerbespeicher')

    def _is_configured(self) -> bool:
        """Check if email service is properly configured"""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    async def send_offer_email(
        self,
        to_email: str,
        customer_name: str,
        offer_number: str,
        offer_text: str,
        valid_until: Optional[datetime] = None,
        pdf_attachment: Optional[bytes] = None,
        custom_message: Optional[str] = None,
    ) -> dict:
        """
        Send offer email to customer.

        Args:
            to_email: Recipient email address
            customer_name: Customer's name for personalization
            offer_number: The offer number for reference
            offer_text: The main offer text content
            valid_until: Offer validity date
            pdf_attachment: Optional PDF bytes to attach
            custom_message: Optional custom message from the user

        Returns:
            dict with status and message
        """
        if not self._is_configured():
            logger.warning("Email service not configured - skipping send")
            return {
                "success": False,
                "message": "Email-Service nicht konfiguriert. Bitte SMTP-Einstellungen prüfen.",
                "simulated": True
            }

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Ihr Angebot {offer_number} - PV-Speichersystem"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email

            # SECURITY: Sanitize all user-provided content to prevent XSS
            safe_customer_name = sanitize_for_html(customer_name)
            safe_offer_number = sanitize_for_html(offer_number)
            safe_offer_text = sanitize_for_html(offer_text[:500])
            safe_custom_message = sanitize_for_html(custom_message) if custom_message else ""

            # Build email content
            validity_text = ""
            if valid_until:
                validity_text = f"<p><strong>Gültig bis:</strong> {valid_until.strftime('%d.%m.%Y')}</p>"

            custom_section = ""
            if safe_custom_message:
                custom_section = f"""
                <div style="background-color: #f0f9ff; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0; color: #1e40af;">{safe_custom_message}</p>
                </div>
                """

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #1e293b; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #ffffff; padding: 30px; border: 1px solid #e2e8f0; }}
                    .footer {{ background: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #64748b; border-radius: 0 0 8px 8px; }}
                    .cta-button {{ display: inline-block; background: #10b981; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 20px 0; }}
                    .highlight {{ background: #ecfdf5; padding: 15px; border-left: 4px solid #10b981; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 style="margin: 0;">Ihr PV-Speicher Angebot</h1>
                        <p style="margin: 10px 0 0 0; opacity: 0.9;">Angebot Nr. {safe_offer_number}</p>
                    </div>
                    <div class="content">
                        <p>Sehr geehrte(r) {safe_customer_name},</p>

                        <p>vielen Dank für Ihr Interesse an unseren PV-Speicherlösungen.
                        Anbei erhalten Sie Ihr individuelles Angebot.</p>

                        {custom_section}

                        <div class="highlight">
                            <p style="margin: 0;"><strong>Angebotsnummer:</strong> {safe_offer_number}</p>
                            {validity_text}
                        </div>

                        <h3>Zusammenfassung</h3>
                        <p>{safe_offer_text}{'...' if len(offer_text) > 500 else ''}</p>

                        <p>Das vollständige Angebot finden Sie im beigefügten PDF-Dokument.</p>

                        <p style="text-align: center;">
                            <a href="#" class="cta-button">Angebot online ansehen</a>
                        </p>

                        <p>Bei Fragen stehen wir Ihnen gerne zur Verfügung.</p>

                        <p>Mit freundlichen Grüßen,<br>
                        <strong>Ihr EWS Team</strong></p>
                    </div>
                    <div class="footer">
                        <p><strong>EWS GmbH</strong></p>
                        <p>Industriestraße 1 | 24983 Handewitt | Deutschland</p>
                        <p>Tel: +49 4608 1234-0 | info@ews-gmbh.de</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Plain text fallback
            text_content = f"""
            Sehr geehrte(r) {customer_name},

            vielen Dank für Ihr Interesse an unseren PV-Speicherlösungen.

            Angebotsnummer: {offer_number}
            {'Gültig bis: ' + valid_until.strftime('%d.%m.%Y') if valid_until else ''}

            {custom_message if custom_message else ''}

            Zusammenfassung:
            {offer_text[:500]}{'...' if len(offer_text) > 500 else ''}

            Das vollständige Angebot finden Sie im beigefügten PDF-Dokument.

            Mit freundlichen Grüßen,
            Ihr EWS Team

            ---
            EWS GmbH | Industriestraße 1 | 24983 Handewitt
            Tel: +49 4608 1234-0 | info@ews-gmbh.de
            """

            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))

            # Attach PDF if provided
            if pdf_attachment:
                pdf_part = MIMEApplication(pdf_attachment, Name=f"Angebot_{offer_number}.pdf")
                pdf_part['Content-Disposition'] = f'attachment; filename="Angebot_{offer_number}.pdf"'
                msg.attach(pdf_part)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Offer email sent successfully to {to_email}")
            return {
                "success": True,
                "message": f"Email erfolgreich an {to_email} gesendet.",
                "simulated": False
            }

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed")
            return {
                "success": False,
                "message": "SMTP-Authentifizierung fehlgeschlagen.",
                "simulated": False
            }
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return {
                "success": False,
                "message": f"Email-Versand fehlgeschlagen: {str(e)}",
                "simulated": False
            }
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return {
                "success": False,
                "message": f"Unerwarteter Fehler: {str(e)}",
                "simulated": False
            }

    async def send_offer_email_simulated(
        self,
        to_email: str,
        customer_name: str,
        offer_number: str,
        offer_text: str,
        valid_until: Optional[datetime] = None,
        custom_message: Optional[str] = None,
    ) -> dict:
        """
        Simulate sending an offer email (for development/demo).
        Logs what would be sent without actually sending.

        Returns:
            dict with simulated status
        """
        logger.info(f"""
        === SIMULATED EMAIL ===
        To: {to_email}
        Subject: Ihr Angebot {offer_number} - PV-Speichersystem
        Customer: {customer_name}
        Valid Until: {valid_until}
        Custom Message: {custom_message}
        Offer Text Preview: {offer_text[:200]}...
        =======================
        """)

        return {
            "success": True,
            "message": f"Email würde an {to_email} gesendet werden (Simulationsmodus).",
            "simulated": True,
            "preview": {
                "to": to_email,
                "subject": f"Ihr Angebot {offer_number} - PV-Speichersystem",
                "customer_name": customer_name,
            }
        }


# Singleton instance
email_service = EmailService()
