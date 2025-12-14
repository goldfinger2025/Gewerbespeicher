"""
PDF Generation Service
Creates professional offer PDFs using ReportLab
"""

import io
import os
from datetime import datetime
from typing import Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY

from app.models.offer import Offer
from app.models.simulation import Simulation
from app.models.project import Project


class PDFService:
    """Service for generating professional PDF offers"""

    # Brand Colors
    PRIMARY_COLOR = colors.HexColor("#2563eb")  # Blue
    SECONDARY_COLOR = colors.HexColor("#10b981")  # Emerald
    ACCENT_COLOR = colors.HexColor("#f59e0b")  # Amber
    TEXT_COLOR = colors.HexColor("#1e293b")  # Slate 900
    LIGHT_BG = colors.HexColor("#f8fafc")  # Slate 50

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.PRIMARY_COLOR,
            spaceAfter=12,
            alignment=TA_CENTER,
        ))

        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.TEXT_COLOR,
            spaceBefore=20,
            spaceAfter=10,
        ))

        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=self.PRIMARY_COLOR,
            spaceBefore=15,
            spaceAfter=8,
            borderPadding=5,
        ))

        # Body text
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.TEXT_COLOR,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
            leading=14,
        ))

        # Small text
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor("#64748b"),
        ))

        # Metric value
        self.styles.add(ParagraphStyle(
            name='MetricValue',
            parent=self.styles['Normal'],
            fontSize=18,
            textColor=self.SECONDARY_COLOR,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
        ))

        # Metric label
        self.styles.add(ParagraphStyle(
            name='MetricLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor("#64748b"),
            alignment=TA_CENTER,
        ))

    def generate_offer_pdf(
        self,
        offer: Offer,
        simulation: Simulation,
        project: Project,
        output_path: Optional[str] = None
    ) -> bytes:
        """
        Generate a professional PDF offer document.

        Args:
            offer: The offer model
            simulation: The simulation model with results
            project: The project model with customer/system data
            output_path: Optional path to save file (if None, returns bytes)

        Returns:
            PDF as bytes
        """
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        # Build document elements
        elements = []

        # Header
        elements.extend(self._build_header(offer, project))

        # Customer Info
        elements.extend(self._build_customer_section(project))

        # System Configuration
        elements.extend(self._build_system_section(project))

        # Simulation Results
        elements.extend(self._build_results_section(simulation))

        # Financial Analysis
        elements.extend(self._build_financial_section(simulation, project))

        # Offer Text (from Claude)
        if offer.offer_text:
            elements.extend(self._build_offer_text_section(offer))

        # Components / BOM
        if offer.components_bom:
            elements.extend(self._build_bom_section(offer))

        # Pricing
        if offer.pricing_breakdown:
            elements.extend(self._build_pricing_section(offer))

        # Terms & Footer
        elements.extend(self._build_footer_section(offer))

        # Build PDF
        doc.build(elements, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)

        pdf_bytes = buffer.getvalue()
        buffer.close()

        # Optionally save to file
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)

        return pdf_bytes

    def _build_header(self, offer: Offer, project: Project) -> list:
        """Build document header with logo and offer info"""
        elements = []

        # Company name as text header (since we don't have a logo file)
        header_data = [
            [
                Paragraph("<b>EWS GmbH</b><br/>Gewerbespeicher Planner", self.styles['CustomBody']),
                Paragraph(
                    f"<b>Angebot Nr. {offer.offer_number or 'ENTWURF'}</b><br/>"
                    f"Datum: {offer.offer_date.strftime('%d.%m.%Y') if offer.offer_date else datetime.now().strftime('%d.%m.%Y')}",
                    ParagraphStyle('RightAlign', parent=self.styles['CustomBody'], alignment=TA_RIGHT)
                )
            ]
        ]

        header_table = Table(header_data, colWidths=[9*cm, 8*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10*mm))

        # Main title
        elements.append(Paragraph(
            "Angebot PV-Speichersystem",
            self.styles['CustomTitle']
        ))
        elements.append(Paragraph(
            f"für {project.customer_company or project.customer_name}",
            ParagraphStyle('Subtitle', parent=self.styles['CustomBody'], alignment=TA_CENTER, fontSize=12)
        ))
        elements.append(Spacer(1, 10*mm))
        elements.append(HRFlowable(width="100%", thickness=1, color=self.PRIMARY_COLOR))
        elements.append(Spacer(1, 5*mm))

        return elements

    def _build_customer_section(self, project: Project) -> list:
        """Build customer information section"""
        elements = []

        elements.append(Paragraph("Kundeninformationen", self.styles['SectionHeader']))

        customer_data = [
            ["Kunde:", project.customer_name or "-"],
            ["Firma:", project.customer_company or "-"],
            ["Adresse:", f"{project.address or '-'}, {project.postal_code or ''} {project.city or ''}"],
            ["E-Mail:", project.customer_email or "-"],
        ]

        table = Table(customer_data, colWidths=[4*cm, 13*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.TEXT_COLOR),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 5*mm))

        return elements

    def _build_system_section(self, project: Project) -> list:
        """Build system configuration section"""
        elements = []

        elements.append(Paragraph("Systemkonfiguration", self.styles['SectionHeader']))

        # PV System
        pv_data = [
            ["PV-Anlage", ""],
            ["Leistung:", f"{project.pv_peak_power_kw or 0:.1f} kWp"],
            ["Ausrichtung:", project.pv_orientation or "Süd"],
            ["Neigung:", f"{project.pv_tilt_angle or 30}°"],
        ]

        # Battery System
        battery_data = [
            ["Batteriespeicher", ""],
            ["Kapazität:", f"{project.battery_capacity_kwh or 0:.1f} kWh"],
            ["Leistung:", f"{project.battery_power_kw or (project.battery_capacity_kwh or 0) * 0.5:.1f} kW"],
            ["Hersteller:", project.battery_manufacturer or "-"],
        ]

        # Consumption
        consumption_data = [
            ["Verbrauch", ""],
            ["Jahresverbrauch:", f"{project.annual_consumption_kwh or 0:,.0f} kWh".replace(",", ".")],
            ["Strompreis:", f"{(project.electricity_price_eur_kwh or 0.30) * 100:.1f} ct/kWh"],
        ]

        # Create side-by-side tables
        system_table = Table([
            [
                self._create_info_table(pv_data),
                self._create_info_table(battery_data),
                self._create_info_table(consumption_data),
            ]
        ], colWidths=[5.7*cm, 5.7*cm, 5.7*cm])

        system_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(system_table)
        elements.append(Spacer(1, 5*mm))

        return elements

    def _create_info_table(self, data: list) -> Table:
        """Create a formatted info table"""
        table = Table(data, colWidths=[3.5*cm, 2*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.TEXT_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.PRIMARY_COLOR),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, 0), (-1, 0), self.LIGHT_BG),
        ]))
        return table

    def _build_results_section(self, simulation: Simulation) -> list:
        """Build simulation results section with KPI cards"""
        elements = []

        elements.append(Paragraph("Simulationsergebnisse", self.styles['SectionHeader']))

        # KPI Cards
        kpis = [
            (f"{simulation.autonomy_degree_percent or 0:.1f}%", "Autarkiegrad"),
            (f"{simulation.self_consumption_ratio_percent or 0:.1f}%", "Eigenverbrauch"),
            (f"{(simulation.pv_generation_kwh or 0)/1000:,.1f} MWh".replace(",", "."), "PV-Ertrag/Jahr"),
            (f"{simulation.battery_discharge_cycles or 0:.0f}", "Batteriezyklen/Jahr"),
        ]

        kpi_cells = []
        for value, label in kpis:
            kpi_cells.append([
                Paragraph(value, self.styles['MetricValue']),
                Paragraph(label, self.styles['MetricLabel']),
            ])

        kpi_table = Table(
            [[self._create_kpi_card(kpi_cells[i]) for i in range(4)]],
            colWidths=[4.25*cm] * 4
        )
        kpi_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(kpi_table)
        elements.append(Spacer(1, 5*mm))

        # Energy Balance Table
        elements.append(Paragraph("Energiebilanz", self.styles['CustomSubtitle']))

        energy_data = [
            ["Kennzahl", "Wert", "Einheit"],
            ["PV-Erzeugung", f"{simulation.pv_generation_kwh or 0:,.0f}".replace(",", "."), "kWh/Jahr"],
            ["Eigenverbrauch", f"{simulation.self_consumed_kwh or 0:,.0f}".replace(",", "."), "kWh/Jahr"],
            ["Netzeinspeisung", f"{simulation.fed_to_grid_kwh or 0:,.0f}".replace(",", "."), "kWh/Jahr"],
            ["Netzbezug", f"{simulation.consumed_from_grid_kwh or 0:,.0f}".replace(",", "."), "kWh/Jahr"],
        ]

        energy_table = Table(energy_data, colWidths=[7*cm, 5*cm, 5*cm])
        energy_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.LIGHT_BG]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(energy_table)
        elements.append(Spacer(1, 5*mm))

        return elements

    def _create_kpi_card(self, content: list) -> Table:
        """Create a KPI card table"""
        table = Table(content, colWidths=[4*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.LIGHT_BG),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ]))
        return table

    def _build_financial_section(self, simulation: Simulation, project: Project) -> list:
        """Build financial analysis section"""
        elements = []

        elements.append(Paragraph("Wirtschaftlichkeitsanalyse", self.styles['SectionHeader']))

        # Financial KPIs
        financial_data = [
            ["Kennzahl", "Wert"],
            ["Jährliche Einsparung", f"{simulation.annual_savings_eur or 0:,.0f} €".replace(",", ".")],
            ["Gesamteinsparung (20 Jahre)", f"{simulation.total_savings_eur or 0:,.0f} €".replace(",", ".")],
            ["Amortisationszeit", f"{simulation.payback_period_years or 0:.1f} Jahre"],
            ["Kapitalwert (NPV)", f"{simulation.npv_eur or 0:,.0f} €".replace(",", ".")],
            ["Interne Rendite (IRR)", f"{simulation.irr_percent or 0:.1f} %"],
        ]

        fin_table = Table(financial_data, colWidths=[9*cm, 8*cm])
        fin_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.SECONDARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.LIGHT_BG]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(fin_table)
        elements.append(Spacer(1, 5*mm))

        return elements

    def _build_offer_text_section(self, offer: Offer) -> list:
        """Build offer text section (Claude-generated content)"""
        elements = []

        elements.append(Paragraph("Angebotsbeschreibung", self.styles['SectionHeader']))

        # Split text into paragraphs and render
        paragraphs = offer.offer_text.split('\n\n')
        for para in paragraphs:
            if para.strip():
                elements.append(Paragraph(para.strip(), self.styles['CustomBody']))

        elements.append(Spacer(1, 5*mm))

        return elements

    def _build_bom_section(self, offer: Offer) -> list:
        """Build Bill of Materials section"""
        elements = []

        elements.append(Paragraph("Komponentenliste", self.styles['SectionHeader']))

        bom = offer.components_bom
        if isinstance(bom, list) and len(bom) > 0:
            bom_data = [["Pos.", "Komponente", "Hersteller", "Menge", "Einheit"]]

            for i, item in enumerate(bom, 1):
                bom_data.append([
                    str(i),
                    item.get('name', '-'),
                    item.get('manufacturer', '-'),
                    str(item.get('quantity', 1)),
                    item.get('unit', 'Stk.')
                ])

            bom_table = Table(bom_data, colWidths=[1.5*cm, 7*cm, 4*cm, 2*cm, 2.5*cm])
            bom_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_COLOR),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (3, 0), (3, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.LIGHT_BG]),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))

            elements.append(bom_table)

        elements.append(Spacer(1, 5*mm))

        return elements

    def _build_pricing_section(self, offer: Offer) -> list:
        """Build pricing breakdown section"""
        elements = []

        elements.append(Paragraph("Preisübersicht", self.styles['SectionHeader']))

        pricing = offer.pricing_breakdown
        if isinstance(pricing, dict):
            pricing_data = [["Position", "Netto", "MwSt.", "Brutto"]]

            # Individual items
            items = pricing.get('items', [])
            for item in items:
                net = item.get('net_price', 0)
                vat = net * 0.19
                gross = net + vat
                pricing_data.append([
                    item.get('description', '-'),
                    f"{net:,.2f} €".replace(",", "."),
                    f"{vat:,.2f} €".replace(",", "."),
                    f"{gross:,.2f} €".replace(",", "."),
                ])

            # Totals
            total_net = pricing.get('total_net', 0)
            total_vat = pricing.get('total_vat', total_net * 0.19)
            total_gross = pricing.get('total_gross', total_net * 1.19)

            pricing_data.append(["", "", "", ""])
            pricing_data.append([
                "Gesamtsumme",
                f"{total_net:,.2f} €".replace(",", "."),
                f"{total_vat:,.2f} €".replace(",", "."),
                f"{total_gross:,.2f} €".replace(",", "."),
            ])

            pricing_table = Table(pricing_data, colWidths=[7*cm, 3.5*cm, 3.5*cm, 3*cm])
            pricing_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.ACCENT_COLOR),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor("#e2e8f0")),
                ('LINEABOVE', (0, -1), (-1, -1), 2, self.ACCENT_COLOR),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, self.LIGHT_BG]),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))

            elements.append(pricing_table)

        elements.append(Spacer(1, 5*mm))

        return elements

    def _build_footer_section(self, offer: Offer) -> list:
        """Build terms and footer section"""
        elements = []

        elements.append(Spacer(1, 10*mm))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
        elements.append(Spacer(1, 5*mm))

        # Validity
        if offer.valid_until:
            validity_text = f"Dieses Angebot ist gültig bis zum {offer.valid_until.strftime('%d.%m.%Y')}."
        else:
            validity_text = "Dieses Angebot ist 30 Tage ab Ausstellungsdatum gültig."

        elements.append(Paragraph(validity_text, self.styles['CustomBody']))
        elements.append(Spacer(1, 5*mm))

        # Terms
        terms = """
        <b>Zahlungsbedingungen:</b> 50% bei Auftragserteilung, 50% nach Inbetriebnahme.<br/>
        <b>Lieferzeit:</b> ca. 4-6 Wochen nach Auftragserteilung.<br/>
        <b>Garantie:</b> 10 Jahre Produktgarantie, 25 Jahre Leistungsgarantie auf PV-Module.<br/>
        """
        elements.append(Paragraph(terms, self.styles['SmallText']))

        elements.append(Spacer(1, 10*mm))

        # Signature area
        sig_data = [
            ["_" * 30, "", "_" * 30],
            ["Ort, Datum", "", "Unterschrift Kunde"],
        ]
        sig_table = Table(sig_data, colWidths=[6*cm, 5*cm, 6*cm])
        sig_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 1), (-1, 1), 5),
        ]))
        elements.append(sig_table)

        elements.append(Spacer(1, 15*mm))

        # Company footer
        footer_text = """
        <b>EWS GmbH</b> | Industriestraße 1 | 24983 Handewitt | Deutschland<br/>
        Tel: +49 4608 1234-0 | E-Mail: info@ews-gmbh.de | Web: www.ews-gmbh.de
        """
        elements.append(Paragraph(footer_text, ParagraphStyle(
            'Footer',
            parent=self.styles['SmallText'],
            alignment=TA_CENTER
        )))

        return elements

    def _add_page_number(self, canvas, doc):
        """Add page number to each page"""
        page_num = canvas.getPageNumber()
        text = f"Seite {page_num}"
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawRightString(doc.pagesize[0] - 2*cm, 1.5*cm, text)
        canvas.restoreState()


# Singleton instance
pdf_service = PDFService()
