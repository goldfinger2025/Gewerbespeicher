#!/usr/bin/env python3
"""
Erstellt eine PowerPoint-Präsentation für den Gewerbespeicher Planner.
Marktwert-Validierung und Anwendungsübersicht für Management-Präsentation.
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# Farben
DARK_BLUE = RGBColor(0x1B, 0x2A, 0x4A)
ACCENT_BLUE = RGBColor(0x2E, 0x86, 0xAB)
ACCENT_GREEN = RGBColor(0x28, 0xA7, 0x45)
ACCENT_ORANGE = RGBColor(0xF0, 0x93, 0x19)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xF0, 0xF2, 0xF5)
MEDIUM_GRAY = RGBColor(0x6C, 0x75, 0x7D)
TEXT_DARK = RGBColor(0x21, 0x25, 0x29)
SUBTLE_BG = RGBColor(0xE8, 0xED, 0xF2)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

SW = prs.slide_width
SH = prs.slide_height


def add_shape(slide, left, top, width, height, fill_color=None, line_color=None, shape_type=MSO_SHAPE.RECTANGLE):
    shape = slide.shapes.add_shape(shape_type, left, top, width, height)
    shape.line.fill.background()
    if fill_color:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_color
    if line_color:
        shape.line.color.rgb = line_color
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    return shape


def add_text_box(slide, left, top, width, height, text, font_size=14, bold=False, color=TEXT_DARK, alignment=PP_ALIGN.LEFT, font_name="Calibri"):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font_name
    p.alignment = alignment
    return txBox


def add_kpi_card(slide, left, top, width, height, value, label, accent_color=ACCENT_BLUE):
    """Erstellt eine KPI-Karte mit Wert und Label."""
    card = add_shape(slide, left, top, width, height, fill_color=WHITE)
    # Akzentlinie oben
    add_shape(slide, left, top, width, Pt(4), fill_color=accent_color)
    # Wert
    add_text_box(slide, left + Inches(0.2), top + Inches(0.2), width - Inches(0.4), Inches(0.6),
                 value, font_size=26, bold=True, color=accent_color, alignment=PP_ALIGN.CENTER)
    # Label
    add_text_box(slide, left + Inches(0.1), top + Inches(0.7), width - Inches(0.2), Inches(0.5),
                 label, font_size=11, color=MEDIUM_GRAY, alignment=PP_ALIGN.CENTER)


def add_bullet_block(slide, left, top, width, height, title, items, title_color=ACCENT_BLUE, bullet_char="\u25B8"):
    """Erstellt einen Textblock mit Titel und Aufzählung."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True

    # Titel
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = title_color
    p.font.name = "Calibri"
    p.space_after = Pt(6)

    # Items
    for item in items:
        p = tf.add_paragraph()
        p.text = f"{bullet_char} {item}"
        p.font.size = Pt(12)
        p.font.color.rgb = TEXT_DARK
        p.font.name = "Calibri"
        p.space_after = Pt(3)
        p.level = 0

    return txBox


# ============================================================
# SLIDE 1: Titelfolie + Anwendungsübersicht
# ============================================================
slide1 = prs.slides.add_slide(prs.slide_layouts[6])  # Blank

# Hintergrund
bg = slide1.background
fill = bg.fill
fill.solid()
fill.fore_color.rgb = LIGHT_GRAY

# Header-Balken
add_shape(slide1, 0, 0, SW, Inches(1.8), fill_color=DARK_BLUE)

# Titel
add_text_box(slide1, Inches(0.8), Inches(0.3), Inches(10), Inches(0.6),
             "Gewerbespeicher Planner", font_size=32, bold=True, color=WHITE)
# Untertitel
add_text_box(slide1, Inches(0.8), Inches(0.9), Inches(10), Inches(0.5),
             "KI-gestutzte Planungs- & Angebotssoftware fur gewerbliche PV-Speichersysteme | EWS GmbH",
             font_size=16, color=RGBColor(0xA0, 0xC0, 0xDF))

# AI-Badge rechts oben
ai_badge = add_shape(slide1, Inches(10.8), Inches(0.35), Inches(2.1), Inches(0.5), fill_color=ACCENT_GREEN)
add_text_box(slide1, Inches(10.8), Inches(0.38), Inches(2.1), Inches(0.5),
             "\u2728 Built with AI", font_size=14, bold=True, color=WHITE, alignment=PP_ALIGN.CENTER)

# Untertitel-Badge
ai_sub = add_shape(slide1, Inches(10.8), Inches(0.95), Inches(2.1), Inches(0.4), fill_color=RGBColor(0x1D, 0x7A, 0x3A))
add_text_box(slide1, Inches(10.8), Inches(0.95), Inches(2.1), Inches(0.4),
             "Claude AI (Anthropic)", font_size=10, color=WHITE, alignment=PP_ALIGN.CENTER)

# === Hauptbereich: Zwei Spalten ===

# LINKE SPALTE: Was die Anwendung leistet
left_x = Inches(0.6)
col_w = Inches(5.8)

add_text_box(slide1, left_x, Inches(2.1), col_w, Inches(0.4),
             "Was die Anwendung leistet", font_size=18, bold=True, color=DARK_BLUE)

add_bullet_block(slide1, left_x, Inches(2.5), col_w, Inches(2.2),
                 "Kernfunktionen", [
                     "Echtzeit-PV+Batterie-Simulation (pvlib, stundliche Auflosung)",
                     "KI-optimierte Systemdimensionierung & Angebotstexte (Claude Opus)",
                     "Professionelle PDF-Angebotserstellung mit Branding",
                     "Finanzanalyse: ROI, Amortisation, Kapitalwert, interner Zinsfuss",
                     "Multi-Tenant White-Label fur Installateur-Netzwerk",
                 ], title_color=ACCENT_BLUE)

add_bullet_block(slide1, left_x, Inches(4.6), col_w, Inches(1.8),
                 "Integrationen", [
                     "DocuSign (E-Signatur) | HubSpot (CRM) | Google Maps",
                     "PVGIS & Open-Meteo (Wetter-/Ertragsdaten)",
                     "BNetzA-konforme EEG-Einspeisetarife & MaStR-Compliance",
                     "KfW-Forderungsprogramme & Subventionsberechnung",
                 ], title_color=ACCENT_BLUE)

# RECHTE SPALTE: Technologie & KI-Aspekt
right_x = Inches(6.8)
col_w2 = Inches(5.8)

add_text_box(slide1, right_x, Inches(2.1), col_w2, Inches(0.4),
             "Technologie-Stack", font_size=18, bold=True, color=DARK_BLUE)

# Tech-Stack Karten
tech_items = [
    ("Frontend", "Next.js 15, React 19, TypeScript, Tailwind CSS, Recharts"),
    ("Backend", "FastAPI, SQLAlchemy, Pydantic, pvlib-python, asyncpg"),
    ("KI-Integration", "Anthropic Claude Opus 4.5 - Intelligente Angebotsoptimierung"),
    ("Infrastruktur", "Vercel + Railway + Neon (PostgreSQL) + Upstash (Redis)"),
    ("Compliance", "EEG 2023, \u00a714a EnWG, MaStR, KfW-Forderung"),
]

y_pos = Inches(2.6)
for title, desc in tech_items:
    card = add_shape(slide1, right_x, y_pos, col_w2, Inches(0.65), fill_color=WHITE)
    add_text_box(slide1, right_x + Inches(0.15), y_pos + Inches(0.05), Inches(1.6), Inches(0.3),
                 title, font_size=11, bold=True, color=ACCENT_BLUE)
    add_text_box(slide1, right_x + Inches(1.8), y_pos + Inches(0.05), Inches(3.8), Inches(0.55),
                 desc, font_size=10, color=TEXT_DARK)
    y_pos += Inches(0.72)

# Entwicklungs-Status am unteren Rand
add_shape(slide1, Inches(0.6), Inches(6.5), Inches(12.1), Inches(0.7), fill_color=WHITE)
add_text_box(slide1, Inches(0.8), Inches(6.55), Inches(2), Inches(0.3),
             "Entwicklungsstatus:", font_size=12, bold=True, color=DARK_BLUE)

phases = [
    ("\u2705 Phase 1: MVP", Inches(2.8)),
    ("\u2705 Phase 2: KI-Integration", Inches(5.0)),
    ("\u2705 Phase 3: Integrationen", Inches(7.6)),
    ("\u2705 Phase 4: Enterprise", Inches(10.2)),
]
for label, x in phases:
    add_text_box(slide1, x, Inches(6.55), Inches(2.2), Inches(0.3),
                 label, font_size=11, bold=True, color=ACCENT_GREEN, alignment=PP_ALIGN.LEFT)

add_text_box(slide1, Inches(0.8), Inches(6.85), Inches(10), Inches(0.3),
             "Produktionsreife B2B-SaaS-Plattform | 4 Entwicklungsphasen abgeschlossen | KI-gestutzte Entwicklung mit Claude Code",
             font_size=10, color=MEDIUM_GRAY)

# ============================================================
# SLIDE 2: Marktvalidierung & Wettbewerb
# ============================================================
slide2 = prs.slides.add_slide(prs.slide_layouts[6])

bg2 = slide2.background
fill2 = bg2.fill
fill2.solid()
fill2.fore_color.rgb = LIGHT_GRAY

# Header
add_shape(slide2, 0, 0, SW, Inches(1.2), fill_color=DARK_BLUE)
add_text_box(slide2, Inches(0.8), Inches(0.3), Inches(10), Inches(0.5),
             "Marktvalidierung & Wettbewerbsanalyse", font_size=28, bold=True, color=WHITE)
add_text_box(slide2, Inches(0.8), Inches(0.7), Inches(10), Inches(0.4),
             "Quellen: Wood Mackenzie, Mordor Intelligence, Grand View Research, BSW Solar, pv magazine, BNetzA",
             font_size=11, color=RGBColor(0xA0, 0xC0, 0xDF))

# === KPI-Reihe ===
kpi_y = Inches(1.5)
kpi_h = Inches(1.15)
kpi_w = Inches(2.8)
gap = Inches(0.35)

add_kpi_card(slide2, Inches(0.6), kpi_y, kpi_w, kpi_h,
             "24 GWh", "DE Speicherkapazitat 2025\n(+6,57 GWh in 2025)", ACCENT_BLUE)

add_kpi_card(slide2, Inches(0.6) + kpi_w + gap, kpi_y, kpi_w, kpi_h,
             "+34%", "Gewerbespeicher-Wachstum\n(Jan 2026 vs. Jan 2025)", ACCENT_GREEN)

add_kpi_card(slide2, Inches(0.6) + 2 * (kpi_w + gap), kpi_y, kpi_w, kpi_h,
             "$19 Mrd.", "DE Energiespeicher-Markt\n(Gesamtmarkt 2024)", ACCENT_ORANGE)

add_kpi_card(slide2, Inches(0.6) + 3 * (kpi_w + gap), kpi_y, kpi_w, kpi_h,
             "$2,5 Mrd.", "Energiespeicher-Software\n(Global 2023, CAGR 15,1%)", ACCENT_BLUE)

# === Zwei Spalten: Markt + Wettbewerb ===
sec_y = Inches(3.0)

# LINKE SPALTE: Marktzahlen
add_text_box(slide2, Inches(0.6), sec_y, Inches(6), Inches(0.4),
             "Marktumfeld & Wachstumstreiber", font_size=16, bold=True, color=DARK_BLUE)

market_items = [
    "PV-Software-Markt: $1,88 Mrd. (2025) \u2192 $2,81 Mrd. (2034), CAGR 6-9%",
    "C&I Energiespeicher-Markt: $92 Mrd. (2025) \u2192 $164 Mrd. (2030), CAGR 12,3%",
    "Gewerbespeicher DE: 1.248 Systeme im Jan. 2026 (+34% YoY)",
    "575 Stunden negative Strompreise in 2025 \u2013 Speicher wirtschaftlich attraktiv",
    "SaaS-Bewertung: 4-7x ARR fur B2B-Software (Median 7x, SaaS Capital 2025)",
    "Solar Peak Act (Feb 2025): Intelligente Steuerung + Speicher nun Pflicht",
    "EU-Ziel 42,5% Erneuerbare bis 2030 treibt Investitionen",
]

txBox = slide2.shapes.add_textbox(Inches(0.6), sec_y + Inches(0.4), Inches(6), Inches(3.5))
tf = txBox.text_frame
tf.word_wrap = True
for i, item in enumerate(market_items):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.text = f"\u25B8 {item}"
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_DARK
    p.font.name = "Calibri"
    p.space_after = Pt(5)

# RECHTE SPALTE: Wettbewerb
add_text_box(slide2, Inches(7.0), sec_y, Inches(5.5), Inches(0.4),
             "Wettbewerb & Positionierung", font_size=16, bold=True, color=DARK_BLUE)

competitors = [
    ("PV*SOL (Valentin)", "Desktop, ~845\u20ac/Jahr", "Simulation, keine KI", MEDIUM_GRAY),
    ("Eturnity", "SaaS, Abo-Modell", "Kalkulator, kein Speicher-Fokus", MEDIUM_GRAY),
    ("Energy Toolbase", "SaaS, US-fokussiert", "Speicher, keine DE-Compliance", MEDIUM_GRAY),
    ("PVcase / PVsyst", "Enterprise / Desktop", "Grossprojekte, kein Gewerbe-Fokus", MEDIUM_GRAY),
]

comp_y = sec_y + Inches(0.5)
for name, model, gap_text, color in competitors:
    card = add_shape(slide2, Inches(7.0), comp_y, Inches(5.5), Inches(0.55), fill_color=WHITE)
    add_text_box(slide2, Inches(7.15), comp_y + Inches(0.03), Inches(2.2), Inches(0.25),
                 name, font_size=11, bold=True, color=ACCENT_BLUE)
    add_text_box(slide2, Inches(7.15), comp_y + Inches(0.28), Inches(2.2), Inches(0.25),
                 model, font_size=9, color=MEDIUM_GRAY)
    add_text_box(slide2, Inches(9.4), comp_y + Inches(0.1), Inches(3.0), Inches(0.35),
                 gap_text, font_size=10, color=TEXT_DARK)
    comp_y += Inches(0.62)

# Unser USP
usp_y = comp_y + Inches(0.15)
usp_card = add_shape(slide2, Inches(7.0), usp_y, Inches(5.5), Inches(0.9), fill_color=DARK_BLUE)
add_text_box(slide2, Inches(7.15), usp_y + Inches(0.05), Inches(5.2), Inches(0.3),
             "Gewerbespeicher Planner \u2013 Unser USP", font_size=12, bold=True, color=WHITE)
add_text_box(slide2, Inches(7.15), usp_y + Inches(0.35), Inches(5.2), Inches(0.5),
             "KI-Optimierung + DE-Compliance + Multi-Tenant + E2E Workflow\n(Simulation \u2192 Angebot \u2192 Signatur \u2192 CRM)",
             font_size=10, color=RGBColor(0xA0, 0xC0, 0xDF))

# Footer mit Quellen
add_shape(slide2, 0, Inches(6.7), SW, Inches(0.8), fill_color=WHITE)
add_text_box(slide2, Inches(0.6), Inches(6.75), Inches(12), Inches(0.6),
             "Quellen: Wood Mackenzie (2025) | Mordor Intelligence C&I Storage Report | BSW Solar | ESS-News.com | "
             "SaaS Capital Valuation Report 2025 | pv magazine DE | Grand View Research | Precedence Research | BNetzA",
             font_size=9, color=MEDIUM_GRAY)


# ============================================================
# SLIDE 3: Wertdarstellung & Strategische Bedeutung
# ============================================================
slide3 = prs.slides.add_slide(prs.slide_layouts[6])

bg3 = slide3.background
fill3 = bg3.fill
fill3.solid()
fill3.fore_color.rgb = LIGHT_GRAY

# Header
add_shape(slide3, 0, 0, SW, Inches(1.2), fill_color=DARK_BLUE)
add_text_box(slide3, Inches(0.8), Inches(0.3), Inches(10), Inches(0.5),
             "Strategischer Wert & Nachster Schritt", font_size=28, bold=True, color=WHITE)
add_text_box(slide3, Inches(0.8), Inches(0.7), Inches(10), Inches(0.4),
             "Warum diese Anwendung ein strategisches Asset fur EWS GmbH ist",
             font_size=14, color=RGBColor(0xA0, 0xC0, 0xDF))

# AI Badge
ai_badge3 = add_shape(slide3, Inches(10.8), Inches(0.3), Inches(2.1), Inches(0.7), fill_color=ACCENT_GREEN)
add_text_box(slide3, Inches(10.8), Inches(0.33), Inches(2.1), Inches(0.35),
             "\u2728 Built with AI", font_size=13, bold=True, color=WHITE, alignment=PP_ALIGN.CENTER)
add_text_box(slide3, Inches(10.8), Inches(0.6), Inches(2.1), Inches(0.35),
             "Claude Code & Opus", font_size=9, color=WHITE, alignment=PP_ALIGN.CENTER)

# === 3 Wert-Saulen ===
pillar_y = Inches(1.5)
pillar_w = Inches(3.8)
pillar_h = Inches(2.6)
pillar_gap = Inches(0.4)

# Saule 1: Umsatzpotenzial
p1_x = Inches(0.6)
add_shape(slide3, p1_x, pillar_y, pillar_w, pillar_h, fill_color=WHITE)
add_shape(slide3, p1_x, pillar_y, pillar_w, Pt(5), fill_color=ACCENT_BLUE)
add_text_box(slide3, p1_x + Inches(0.2), pillar_y + Inches(0.15), pillar_w - Inches(0.4), Inches(0.3),
             "\U0001F4B0 Umsatzpotenzial", font_size=15, bold=True, color=ACCENT_BLUE)

p1_items = [
    "SaaS-Lizenzmodell pro Installateur/Monat",
    "Skalierbar uber Multi-Tenant-Architektur",
    "C&I Speichermarkt DE: +34% Wachstum YoY",
    "SaaS-Bewertung: 4-7x jahrlicher Umsatz",
    "Zusatzerlorse uber PDF-Angebote & CRM-Leads",
]
p1_box = slide3.shapes.add_textbox(p1_x + Inches(0.2), pillar_y + Inches(0.55), pillar_w - Inches(0.4), Inches(2.0))
p1_tf = p1_box.text_frame
p1_tf.word_wrap = True
for i, item in enumerate(p1_items):
    p = p1_tf.paragraphs[0] if i == 0 else p1_tf.add_paragraph()
    p.text = f"\u25B8 {item}"
    p.font.size = Pt(10.5)
    p.font.color.rgb = TEXT_DARK
    p.font.name = "Calibri"
    p.space_after = Pt(3)

# Saule 2: Wettbewerbsvorteil
p2_x = p1_x + pillar_w + pillar_gap
add_shape(slide3, p2_x, pillar_y, pillar_w, pillar_h, fill_color=WHITE)
add_shape(slide3, p2_x, pillar_y, pillar_w, Pt(5), fill_color=ACCENT_GREEN)
add_text_box(slide3, p2_x + Inches(0.2), pillar_y + Inches(0.15), pillar_w - Inches(0.4), Inches(0.3),
             "\U0001F3AF Wettbewerbsvorteil", font_size=15, bold=True, color=ACCENT_GREEN)

p2_items = [
    "Einzige DE-Losung: KI + Compliance + E2E",
    "Kein Wettbewerber deckt gesamten Workflow ab",
    "Regulatorische Komplexitat als Markteintrittsbarriere",
    "KI-Differenzierung: Intelligente Angebotsoptimierung",
    "White-Label ermoglicht Partnernetzwerk-Skalierung",
]
p2_box = slide3.shapes.add_textbox(p2_x + Inches(0.2), pillar_y + Inches(0.55), pillar_w - Inches(0.4), Inches(2.0))
p2_tf = p2_box.text_frame
p2_tf.word_wrap = True
for i, item in enumerate(p2_items):
    p = p2_tf.paragraphs[0] if i == 0 else p2_tf.add_paragraph()
    p.text = f"\u25B8 {item}"
    p.font.size = Pt(10.5)
    p.font.color.rgb = TEXT_DARK
    p.font.name = "Calibri"
    p.space_after = Pt(3)

# Saule 3: KI-Effizienz
p3_x = p2_x + pillar_w + pillar_gap
add_shape(slide3, p3_x, pillar_y, pillar_w, pillar_h, fill_color=WHITE)
add_shape(slide3, p3_x, pillar_y, pillar_w, Pt(5), fill_color=ACCENT_ORANGE)
add_text_box(slide3, p3_x + Inches(0.2), pillar_y + Inches(0.15), pillar_w - Inches(0.4), Inches(0.3),
             "\u26A1 KI-gestutzte Entwicklung", font_size=15, bold=True, color=ACCENT_ORANGE)

p3_items = [
    "Entwickelt mit Claude Code (Anthropic AI)",
    "Dramatisch beschleunigte Entwicklungszeit",
    "Produktionsreife Qualitat (4 Phasen abgeschlossen)",
    "Mathematisch validierte Berechnungsmodelle",
    "Modernes Tech-Stack (Next.js 15, FastAPI, PostgreSQL)",
]
p3_box = slide3.shapes.add_textbox(p3_x + Inches(0.2), pillar_y + Inches(0.55), pillar_w - Inches(0.4), Inches(2.0))
p3_tf = p3_box.text_frame
p3_tf.word_wrap = True
for i, item in enumerate(p3_items):
    p = p3_tf.paragraphs[0] if i == 0 else p3_tf.add_paragraph()
    p.text = f"\u25B8 {item}"
    p.font.size = Pt(10.5)
    p.font.color.rgb = TEXT_DARK
    p.font.name = "Calibri"
    p.space_after = Pt(3)

# === Zentrale Aussage ===
key_y = Inches(4.35)
add_shape(slide3, Inches(0.6), key_y, Inches(12.1), Inches(1.1), fill_color=DARK_BLUE)
add_text_box(slide3, Inches(0.8), key_y + Inches(0.1), Inches(11.7), Inches(0.4),
             "Kernaussage", font_size=14, bold=True, color=ACCENT_GREEN)
add_text_box(slide3, Inches(0.8), key_y + Inches(0.45), Inches(11.7), Inches(0.6),
             "Der Gewerbespeicher Planner ist eine produktionsreife, KI-gestutzte B2B-SaaS-Plattform, die in einem $19-Mrd.-Markt (DE) "
             "mit +34% Wachstum positioniert ist. Die Kombination aus KI-Optimierung, regulatorischer Compliance und End-to-End-Workflow "
             "ist im deutschen Markt einzigartig und schafft einen nachhaltigen Wettbewerbsvorteil.",
             font_size=12, color=WHITE)

# === Nachste Schritte ===
next_y = Inches(5.7)
add_text_box(slide3, Inches(0.6), next_y, Inches(12), Inches(0.4),
             "Empfohlene nachste Schritte", font_size=16, bold=True, color=DARK_BLUE)

steps = [
    ("1", "Pilotphase", "5-10 Installateure als Beta-Nutzer gewinnen, Feedback sammeln"),
    ("2", "Go-to-Market", "Preismodell definieren, Vertriebskanal uber EWS-Netzwerk aufbauen"),
    ("3", "Skalierung", "Multi-Tenant-Plattform fur Partnernetzwerk ausrollen"),
]

step_x = Inches(0.6)
for num, title, desc in steps:
    card = add_shape(slide3, step_x, next_y + Inches(0.45), Inches(3.7), Inches(0.7), fill_color=WHITE)
    # Nummer-Kreis
    circle = add_shape(slide3, step_x + Inches(0.1), next_y + Inches(0.55), Inches(0.4), Inches(0.4),
                       fill_color=ACCENT_BLUE, shape_type=MSO_SHAPE.OVAL)
    add_text_box(slide3, step_x + Inches(0.1), next_y + Inches(0.55), Inches(0.4), Inches(0.4),
                 num, font_size=14, bold=True, color=WHITE, alignment=PP_ALIGN.CENTER)
    add_text_box(slide3, step_x + Inches(0.6), next_y + Inches(0.5), Inches(3.0), Inches(0.25),
                 title, font_size=12, bold=True, color=DARK_BLUE)
    add_text_box(slide3, step_x + Inches(0.6), next_y + Inches(0.72), Inches(3.0), Inches(0.35),
                 desc, font_size=9, color=MEDIUM_GRAY)
    step_x += Inches(4.1)

# Footer
add_text_box(slide3, Inches(0.6), Inches(7.0), Inches(12), Inches(0.4),
             "Gewerbespeicher Planner | EWS GmbH | Vertraulich | Februar 2026",
             font_size=9, color=MEDIUM_GRAY, alignment=PP_ALIGN.CENTER)

# ============================================================
# SPEICHERN
# ============================================================
output_path = "/home/user/Gewerbespeicher/Gewerbespeicher_Planner_Praesentation.pptx"
prs.save(output_path)
print(f"Prasentation gespeichert: {output_path}")
