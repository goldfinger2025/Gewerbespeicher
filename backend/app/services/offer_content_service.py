"""
Offer Content Service
Generiert vollständige, professionelle Angebotsinhalte

Dieses Modul stellt sicher, dass alle Angebote folgende Pflichtinformationen enthalten:
1. Detaillierte Preisaufschlüsselung
2. Technische Spezifikationen
3. Garantieinformationen
4. Förderinformationen
5. Zahlungsbedingungen

Stand: Dezember 2025
"""

from typing import Dict, List, Optional
from datetime import date

from app.config import (
    INVESTMENT_COSTS_2025,
    EEG_FEED_IN_TARIFFS,
    FOERDERUNGEN,
    SIMULATION_DEFAULTS,
)


def get_pv_cost_per_kwp(pv_kw: float) -> float:
    """Ermittelt PV-Kosten pro kWp basierend auf Anlagengröße"""
    costs = INVESTMENT_COSTS_2025["pv_cost_per_kwp"]
    if pv_kw <= 30:
        return costs["bis_30kwp"]
    elif pv_kw <= 100:
        return costs["30_100kwp"]
    elif pv_kw <= 500:
        return costs["100_500kwp"]
    else:
        return costs["ueber_500kwp"]


def get_battery_cost_per_kwh(battery_kwh: float) -> float:
    """Ermittelt Speicherkosten pro kWh basierend auf Kapazität"""
    costs = INVESTMENT_COSTS_2025["battery_cost_per_kwh"]
    if battery_kwh <= 30:
        return costs["bis_30kwh"]
    elif battery_kwh <= 100:
        return costs["30_100kwh"]
    elif battery_kwh <= 500:
        return costs["100_500kwh"]
    else:
        return costs["ueber_500kwh"]


def generate_pricing_breakdown(
    pv_kw: float,
    battery_kwh: float,
    battery_power_kw: Optional[float] = None,
    include_installation: bool = True,
    discount_percent: float = 0.0
) -> Dict:
    """
    Generiert eine detaillierte Preisaufschlüsselung

    Args:
        pv_kw: PV-Leistung in kWp
        battery_kwh: Speicherkapazität in kWh
        battery_power_kw: Speicherleistung in kW (optional)
        include_installation: Installation inklusive
        discount_percent: Rabatt in Prozent

    Returns:
        Dict mit detaillierter Preisaufschlüsselung
    """
    # Komponentenkosten
    pv_cost_per_kwp = get_pv_cost_per_kwp(pv_kw)
    battery_cost_per_kwh = get_battery_cost_per_kwh(battery_kwh)

    pv_module_cost = pv_kw * pv_cost_per_kwp * 0.50  # ~50% Module
    pv_inverter_cost = pv_kw * pv_cost_per_kwp * 0.20  # ~20% Wechselrichter
    pv_mounting_cost = pv_kw * pv_cost_per_kwp * 0.15  # ~15% Montagesystem
    pv_cable_cost = pv_kw * pv_cost_per_kwp * 0.05  # ~5% Verkabelung
    pv_misc_cost = pv_kw * pv_cost_per_kwp * 0.10  # ~10% Sonstiges

    battery_cells_cost = battery_kwh * battery_cost_per_kwh * 0.70  # ~70% Zellen
    battery_bms_cost = battery_kwh * battery_cost_per_kwh * 0.20  # ~20% BMS
    battery_housing_cost = battery_kwh * battery_cost_per_kwh * 0.10  # ~10% Gehäuse

    pv_subtotal = pv_kw * pv_cost_per_kwp
    battery_subtotal = battery_kwh * battery_cost_per_kwh

    # Fixkosten
    fixed_costs = INVESTMENT_COSTS_2025["fixed_costs"]
    planning_cost = fixed_costs["planung"]
    registration_cost = fixed_costs["anmeldung"]
    commissioning_cost = fixed_costs["inbetriebnahme"]

    # Installation
    installation_cost = 0
    if include_installation:
        installation_cost = (pv_subtotal + battery_subtotal) * INVESTMENT_COSTS_2025["installation_factor"]

    # Zwischensumme
    subtotal = (
        pv_subtotal +
        battery_subtotal +
        planning_cost +
        registration_cost +
        commissioning_cost +
        installation_cost
    )

    # Rabatt
    discount_amount = subtotal * (discount_percent / 100)

    # MwSt prüfen (0% für PV ≤30 kWp seit 2023)
    vat_exempt = pv_kw <= 30
    vat_rate = 0.0 if vat_exempt else 0.19
    vat_amount = (subtotal - discount_amount) * vat_rate

    total = subtotal - discount_amount + vat_amount

    return {
        "komponenten": {
            "pv_anlage": {
                "module": round(pv_module_cost, 2),
                "wechselrichter": round(pv_inverter_cost, 2),
                "montagesystem": round(pv_mounting_cost, 2),
                "verkabelung": round(pv_cable_cost, 2),
                "sonstiges": round(pv_misc_cost, 2),
                "zwischensumme": round(pv_subtotal, 2),
                "preis_pro_kwp": round(pv_cost_per_kwp, 2),
            },
            "batteriespeicher": {
                "batteriezellen": round(battery_cells_cost, 2),
                "bms": round(battery_bms_cost, 2),
                "gehaeuse": round(battery_housing_cost, 2),
                "zwischensumme": round(battery_subtotal, 2),
                "preis_pro_kwh": round(battery_cost_per_kwh, 2),
            }
        },
        "dienstleistungen": {
            "planung": round(planning_cost, 2),
            "netzanmeldung_mastr": round(registration_cost, 2),
            "inbetriebnahme": round(commissioning_cost, 2),
            "installation": round(installation_cost, 2),
        },
        "zusammenfassung": {
            "zwischensumme_netto": round(subtotal, 2),
            "rabatt_prozent": round(discount_percent, 1),
            "rabatt_betrag": round(discount_amount, 2),
            "mwst_befreit": vat_exempt,
            "mwst_satz": round(vat_rate * 100, 0),
            "mwst_betrag": round(vat_amount, 2),
            "gesamtbetrag": round(total, 2),
        },
        "hinweise": {
            "mwst_befreiung": "Gemäß §12 Abs. 3 UStG entfällt die MwSt für PV-Anlagen ≤30 kWp" if vat_exempt else None,
            "preisgueltigkeit": f"Preise gültig bis {date.today().strftime('%d.%m.%Y')} + 30 Tage",
        }
    }


def generate_technical_specs(
    pv_kw: float,
    battery_kwh: float,
    battery_power_kw: Optional[float] = None,
    pv_orientation: str = "south",
    pv_tilt: float = 30.0,
    battery_chemistry: str = "LFP",
    annual_consumption_kwh: float = 0,
    simulation_results: Optional[Dict] = None
) -> Dict:
    """
    Generiert technische Spezifikationen für das Angebot
    """
    # Module berechnen (angenommen 450W Module)
    module_watt = 450
    num_modules = int((pv_kw * 1000) / module_watt) + 1

    # Speicherleistung
    if battery_power_kw is None:
        battery_power_kw = battery_kwh * 0.5  # Typisch C-Rate 0.5

    # Wechselrichter-Größe
    inverter_kva = pv_kw * 1.1  # 10% Überdimensionierung

    # Orientierung Mapping
    orientation_map = {
        "south": "Süd (180°)",
        "south-west": "Süd-West (225°)",
        "south-east": "Süd-Ost (135°)",
        "east": "Ost (90°)",
        "west": "West (270°)",
    }

    specs = {
        "pv_anlage": {
            "nennleistung_kwp": round(pv_kw, 2),
            "anzahl_module": num_modules,
            "modulleistung_wp": module_watt,
            "wechselrichter_kva": round(inverter_kva, 1),
            "ausrichtung": orientation_map.get(pv_orientation, pv_orientation),
            "neigung_grad": pv_tilt,
            "erwarteter_ertrag_kwh_pro_kwp": 950,  # Deutschland Mittel
            "erwarteter_jahresertrag_kwh": round(pv_kw * 950, 0),
            "degradation_pro_jahr": f"{SIMULATION_DEFAULTS['pv_degradation_jahr'] * 100}%",
            "lebensdauer_jahre": SIMULATION_DEFAULTS["pv_lifetime_years"],
        },
        "batteriespeicher": {
            "kapazitaet_kwh": round(battery_kwh, 1),
            "nutzbare_kapazitaet_kwh": round(battery_kwh * 0.8, 1),  # 80% nutzbar
            "nennleistung_kw": round(battery_power_kw, 1),
            "technologie": battery_chemistry,
            "zyklenlebensdauer": SIMULATION_DEFAULTS["battery_cycle_life"],
            "roundtrip_effizienz": f"{SIMULATION_DEFAULTS['battery_roundtrip_efficiency'] * 100}%",
            "soc_bereich": f"{SIMULATION_DEFAULTS['battery_soc_min'] * 100}-{SIMULATION_DEFAULTS['battery_soc_max'] * 100}%",
            "kalendarische_lebensdauer_jahre": SIMULATION_DEFAULTS["battery_calendar_life_years"],
        },
        "gesamtsystem": {
            "jahresverbrauch_kwh": round(annual_consumption_kwh, 0) if annual_consumption_kwh else None,
            "eigenverbrauchsquote": simulation_results.get("self_consumption_ratio_percent") if simulation_results else None,
            "autarkiegrad": simulation_results.get("autonomy_degree_percent") if simulation_results else None,
            "co2_einsparung_tonnen_pro_jahr": round(pv_kw * 950 * 0.363 / 1000, 1),
        }
    }

    return specs


def generate_warranty_info(
    pv_kw: float,
    battery_kwh: float,
    include_extended: bool = False
) -> Dict:
    """
    Generiert Garantieinformationen
    """
    return {
        "pv_module": {
            "produktgarantie_jahre": 12 if include_extended else 10,
            "leistungsgarantie_jahre": 25,
            "leistungsgarantie_prozent": 80,
            "beschreibung": "Linear abnehmende Leistungsgarantie auf 80% nach 25 Jahren"
        },
        "wechselrichter": {
            "herstellergarantie_jahre": 5,
            "erweiterbar_auf_jahre": 15,
            "garantieerweiterung_kosten": "auf Anfrage",
        },
        "batteriespeicher": {
            "herstellergarantie_jahre": 10,
            "zyklengarantie": SIMULATION_DEFAULTS["battery_cycle_life"],
            "kapazitaetsgarantie_prozent": 70,
            "beschreibung": "Mindestens 70% Kapazität nach 10 Jahren oder 6.000 Zyklen"
        },
        "installation": {
            "gewaehrleistung_jahre": 2,
            "beschreibung": "Gesetzliche Gewährleistung auf Installation und Montage"
        },
        "gesamt": {
            "ansprechpartner": "Service-Hotline",
            "reaktionszeit": "24-48 Stunden",
            "vor_ort_service": True,
        }
    }


def generate_subsidy_info(
    pv_kw: float,
    battery_kwh: float,
    bundesland: Optional[str] = None,
    annual_consumption_kwh: float = 0
) -> Dict:
    """
    Generiert Förderinformationen
    """
    subsidies = {
        "bund": [],
        "land": [],
        "hinweise": [],
    }

    # KfW 270
    kfw = FOERDERUNGEN["bund"]["kfw_270"]
    subsidies["bund"].append({
        "name": kfw["name"],
        "typ": kfw["typ"],
        "beschreibung": f"Kredit bis 100% der Investition, effektiver Jahreszins ab {kfw['effektivzins_ab']}%",
        "bedingung": kfw["antragstellung"],
        "url": kfw["url"],
        "verfuegbar": kfw["aktiv"],
    })

    # MwSt-Befreiung
    if pv_kw <= 30:
        mwst = FOERDERUNGEN["bund"]["mwst_befreiung"]
        subsidies["bund"].append({
            "name": mwst["name"],
            "typ": mwst["typ"],
            "beschreibung": "0% MwSt auf PV-Anlagen ≤30 kWp (automatisch)",
            "ersparnis_prozent": 19,
            "verfuegbar": True,
        })

    # Länderprogramme
    if bundesland and bundesland in FOERDERUNGEN["laender"]:
        land_prog = FOERDERUNGEN["laender"][bundesland]
        subsidies["land"].append({
            "bundesland": land_prog["name"],
            "programm": land_prog.get("programm", "Aktuelles Programm prüfen"),
            "verfuegbar": land_prog.get("aktiv", False),
            "hinweis": land_prog.get("hinweis"),
            "url": land_prog.get("url"),
        })

    # EEG-Vergütung
    eeg_rate = EEG_FEED_IN_TARIFFS["teileinspeisung"]["bis_10kwp"] if pv_kw <= 10 else EEG_FEED_IN_TARIFFS["teileinspeisung"]["10_40kwp"]
    subsidies["hinweise"].append({
        "typ": "EEG-Einspeisevergütung",
        "rate": f"{eeg_rate * 100:.2f} ct/kWh",
        "laufzeit": "20 Jahre ab Inbetriebnahme",
        "stand": EEG_FEED_IN_TARIFFS["stand"],
    })

    return subsidies


def generate_payment_terms() -> str:
    """Generiert Standard-Zahlungsbedingungen"""
    return """ZAHLUNGSBEDINGUNGEN

1. Anzahlung: 30% des Gesamtbetrags bei Auftragserteilung
2. Abschlagszahlung: 40% bei Lieferung der Komponenten
3. Schlussrechnung: 30% nach erfolgreicher Inbetriebnahme und Abnahme

Zahlungsziel: 14 Tage netto nach Rechnungserhalt

Bei Finanzierung über KfW-Kredit gelten gesonderte Zahlungsmodalitäten.

Eigentumssvorbehalt: Die gelieferte Ware bleibt bis zur vollständigen Bezahlung
Eigentum des Auftragnehmers."""


def generate_service_packages() -> List[Dict]:
    """Generiert verfügbare Service-Pakete"""
    return [
        {
            "name": "Basis",
            "preis_pro_jahr": 0,
            "beschreibung": "Gesetzliche Gewährleistung",
            "leistungen": [
                "2 Jahre Gewährleistung auf Installation",
                "Technischer Support per E-Mail",
                "Online-Monitoring",
            ],
            "empfohlen": False,
        },
        {
            "name": "Comfort",
            "preis_pro_jahr": 199,
            "beschreibung": "Jährliche Wartung inklusive",
            "leistungen": [
                "Alle Basis-Leistungen",
                "Jährliche Inspektion vor Ort",
                "Reinigung der Module",
                "Ertragsprüfung und Optimierung",
                "Prioritärer Support",
            ],
            "empfohlen": True,
        },
        {
            "name": "Premium",
            "preis_pro_jahr": 399,
            "beschreibung": "Rundum-Sorglos-Paket",
            "leistungen": [
                "Alle Comfort-Leistungen",
                "Erweiterte Garantie auf 15 Jahre",
                "24h Notfall-Hotline",
                "Kostenlose Reparaturen (außer Verschleiß)",
                "Versicherung gegen Elementarschäden",
            ],
            "empfohlen": False,
        }
    ]


def generate_complete_offer_content(
    pv_kw: float,
    battery_kwh: float,
    battery_power_kw: Optional[float] = None,
    simulation_results: Optional[Dict] = None,
    project_data: Optional[Dict] = None,
    bundesland: Optional[str] = None,
    discount_percent: float = 0.0,
) -> Dict:
    """
    Generiert vollständige Angebotsinhalte für professionelle Angebote

    Returns:
        Dict mit allen Angebotsabschnitten:
        - pricing_breakdown
        - technical_specs
        - warranty_info
        - subsidy_info
        - payment_terms
        - service_packages
    """
    annual_consumption = 0
    pv_orientation = "south"
    pv_tilt = 30.0
    battery_chemistry = "LFP"

    if project_data:
        annual_consumption = project_data.get("annual_consumption_kwh", 0)
        pv_orientation = project_data.get("pv_orientation", "south")
        pv_tilt = project_data.get("pv_tilt_angle", 30.0)
        battery_chemistry = project_data.get("battery_chemistry", "LFP")
        bundesland = bundesland or project_data.get("bundesland")

    return {
        "pricing_breakdown": generate_pricing_breakdown(
            pv_kw=pv_kw,
            battery_kwh=battery_kwh,
            battery_power_kw=battery_power_kw,
            discount_percent=discount_percent,
        ),
        "technical_specs": generate_technical_specs(
            pv_kw=pv_kw,
            battery_kwh=battery_kwh,
            battery_power_kw=battery_power_kw,
            pv_orientation=pv_orientation,
            pv_tilt=pv_tilt,
            battery_chemistry=battery_chemistry,
            annual_consumption_kwh=annual_consumption,
            simulation_results=simulation_results,
        ),
        "warranty_info": generate_warranty_info(pv_kw, battery_kwh),
        "subsidy_info": generate_subsidy_info(
            pv_kw=pv_kw,
            battery_kwh=battery_kwh,
            bundesland=bundesland,
            annual_consumption_kwh=annual_consumption,
        ),
        "payment_terms": generate_payment_terms(),
        "service_packages": generate_service_packages(),
        "terms_reference": "Es gelten unsere Allgemeinen Geschäftsbedingungen (AGB), "
                          "einsehbar unter www.ews-energie.de/agb",
    }
