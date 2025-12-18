"""
Gewerbespeicher API Endpoints
=============================

Spezialisierte Endpoints für gewerbliche PV-Speicher-Anwendungen:
- Peak-Shaving-Analyse und ROI-Berechnung
- Compliance-Checklisten für Installateure
- EEG-Vergütung und Förderinformationen
- §14a EnWG Informationen

Stand: Dezember 2025
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import numpy as np

from app.services.peak_shaving_service import get_peak_shaving_service
from app.services.compliance_service import get_compliance_service
from app.services.emergency_power_service import get_emergency_power_service
from app.config import (
    EEG_FEED_IN_TARIFFS,
    INVESTMENT_COSTS_2025,
    LEISTUNGSPREISE_EUR_KW_JAHR,
    FOERDERUNGEN,
    MASTR_PFLICHTEN,
    SIMULATION_DEFAULTS,
)

router = APIRouter()


# ============ PYDANTIC MODELS ============

class PeakShavingRequest(BaseModel):
    """Anfrage für Peak-Shaving-Analyse"""
    load_profile_kw: List[float] = Field(
        ...,
        description="Lastprofil in kW (8760 Werte für Jahr bei Stundenwerten, 35040 für 15-Min)"
    )
    battery_capacity_kwh: float = Field(..., gt=0, description="Speicherkapazität in kWh")
    battery_power_kw: float = Field(..., gt=0, description="Speicherleistung in kW")
    leistungspreis_eur_kw: Optional[float] = Field(
        None,
        description="Leistungspreis in €/kW/Jahr (Standard: 100)"
    )
    leistungspreis_kategorie: Optional[str] = Field(
        "mittel",
        description="Kategorie: niedrig, mittel, hoch, sehr_hoch, extrem"
    )
    interval_minutes: int = Field(15, description="Messintervall in Minuten (15 oder 60)")


class PeakShavingEconomicsRequest(BaseModel):
    """Anfrage für Peak-Shaving-Wirtschaftlichkeit"""
    original_peak_kw: float = Field(..., gt=0)
    target_peak_kw: float = Field(..., gt=0)
    battery_capacity_kwh: float = Field(..., gt=0)
    battery_power_kw: float = Field(..., gt=0)
    leistungspreis_eur_kw: float = Field(100.0, gt=0)
    battery_cost_per_kwh: float = Field(600.0, gt=0)


class ComplianceRequest(BaseModel):
    """Anfrage für Compliance-Checkliste"""
    pv_kwp: float = Field(..., gt=0, description="PV-Leistung in kWp")
    battery_kwh: float = Field(..., gt=0, description="Speicherkapazität in kWh")
    battery_power_kw: float = Field(..., gt=0, description="Speicherleistung in kW")
    jahresverbrauch_kwh: float = Field(..., gt=0, description="Jahresverbrauch in kWh")
    bundesland: Optional[str] = Field(None, description="Bundesland-Kürzel (BY, NW, etc.)")
    inbetriebnahme_datum: Optional[str] = Field(
        None,
        description="Geplantes Inbetriebnahmedatum (YYYY-MM-DD)"
    )
    eeg_typ: str = Field("teileinspeisung", description="teileinspeisung oder volleinspeisung")


class InvestmentCalcRequest(BaseModel):
    """Anfrage für Investitionskosten-Berechnung"""
    pv_kwp: float = Field(..., gt=0)
    battery_kwh: float = Field(..., gt=0)
    include_installation: bool = Field(True)


class EmergencyPowerAnalysisRequest(BaseModel):
    """Anfrage für Notstrom-Analyse"""
    critical_loads_kw: List[float] = Field(
        ...,
        description="Liste der kritischen Lasten in kW"
    )
    battery_capacity_kwh: float = Field(..., gt=0, description="Speicherkapazität in kWh")
    battery_power_kw: float = Field(..., gt=0, description="Speicherleistung in kW")
    required_backup_hours: float = Field(
        4.0,
        gt=0,
        description="Gewünschte Backup-Dauer in Stunden"
    )
    pv_kwp: Optional[float] = Field(None, gt=0, description="PV-Leistung für Szenario mit PV-Unterstützung")
    current_soc: float = Field(0.9, ge=0.1, le=1.0, description="Aktueller Ladezustand (0.1-1.0)")


class BlackoutSimulationRequest(BaseModel):
    """Anfrage für Blackout-Simulation"""
    load_profile_kw: List[float] = Field(
        ...,
        description="Normales Lastprofil in kW (8760 oder 35040 Werte)"
    )
    battery_capacity_kwh: float = Field(..., gt=0)
    battery_power_kw: float = Field(..., gt=0)
    critical_loads_kw: float = Field(..., gt=0, description="Gesamtleistung kritischer Lasten")
    pv_profile_kw: Optional[List[float]] = Field(
        None,
        description="PV-Erzeugungsprofil (gleiche Länge wie load_profile)"
    )
    outage_start_hour: int = Field(..., ge=0, description="Stunde des Ausfallbeginns (0-8759)")
    outage_duration_hours: float = Field(..., gt=0, description="Dauer des Ausfalls in Stunden")
    initial_soc: float = Field(0.8, ge=0.1, le=1.0, description="SOC bei Ausfallbeginn")
    interval_minutes: int = Field(15, description="Zeitintervall (15 oder 60)")


class CriticalLoadItem(BaseModel):
    """Einzelne kritische Last"""
    name: str = Field(..., description="Name der Last (z.B. 'Kühlanlage')")
    power_kw: float = Field(..., gt=0, description="Leistung in kW")
    priority: int = Field(1, ge=1, le=5, description="Priorität (1=höchste)")


class EmergencyScenarioRequest(BaseModel):
    """Anfrage für Notstrom-Szenario-Analyse"""
    battery_capacity_kwh: float = Field(..., gt=0)
    battery_power_kw: float = Field(..., gt=0)
    critical_loads: List[CriticalLoadItem]
    pv_kwp: Optional[float] = Field(None, gt=0)


# ============ PEAK-SHAVING ENDPOINTS ============

@router.post("/peak-shaving/analyze", response_model=Dict[str, Any])
async def analyze_peak_shaving(request: PeakShavingRequest):
    """
    Analysiert ein Lastprofil auf Peak-Shaving-Potenzial

    Gibt zurück:
    - Lastprofil-Statistiken
    - Top-Lastspitzen
    - Szenarien mit verschiedenen Reduktionszielen
    - Wirtschaftlichkeitsberechnung
    """
    service = get_peak_shaving_service(
        leistungspreis_eur_kw=request.leistungspreis_eur_kw,
        leistungspreis_kategorie=request.leistungspreis_kategorie
    )

    load_array = np.array(request.load_profile_kw)

    if len(load_array) < 100:
        raise HTTPException(
            status_code=400,
            detail="Lastprofil zu kurz. Mindestens 100 Datenpunkte erforderlich."
        )

    result = service.full_analysis(
        load_profile_kw=load_array,
        battery_capacity_kwh=request.battery_capacity_kwh,
        battery_power_kw=request.battery_power_kw,
        interval_minutes=request.interval_minutes
    )

    return result


@router.post("/peak-shaving/economics", response_model=Dict[str, Any])
async def calculate_peak_shaving_economics(request: PeakShavingEconomicsRequest):
    """
    Berechnet die Wirtschaftlichkeit einer Peak-Shaving-Lösung

    Gibt zurück:
    - Investitionskosten
    - Jährliche Ersparnis durch Leistungspreisreduktion
    - Amortisationszeit
    - NPV über 15 Jahre
    """
    service = get_peak_shaving_service(
        leistungspreis_eur_kw=request.leistungspreis_eur_kw
    )

    result = service.calculate_peak_shaving_economics(
        original_peak_kw=request.original_peak_kw,
        target_peak_kw=request.target_peak_kw,
        battery_capacity_kwh=request.battery_capacity_kwh,
        battery_power_kw=request.battery_power_kw,
        battery_cost_per_kwh=request.battery_cost_per_kwh
    )

    return result


@router.get("/peak-shaving/leistungspreise")
async def get_leistungspreise():
    """
    Gibt die Leistungspreis-Kategorien zurück

    Leistungspreise sind regional sehr unterschiedlich (60-440 €/kW/Jahr).
    Diese Kategorien dienen als Orientierung.
    """
    return {
        "kategorien": LEISTUNGSPREISE_EUR_KW_JAHR,
        "erlaeuterung": {
            "niedrig": "Ländliche Gebiete, kleine EVU",
            "mittel": "Durchschnitt Deutschland",
            "hoch": "Städtische Gebiete",
            "sehr_hoch": "Ballungsräume",
            "extrem": "Spitzennetze (z.B. München)"
        },
        "hinweis": "Ab 100.000 kWh/Jahr Verbrauch erfolgt 15-Minuten-Leistungsmessung (RLM)",
        "schwelle_rlm_kwh": 100000
    }


# ============ COMPLIANCE ENDPOINTS ============

@router.post("/compliance/checklist", response_model=Dict[str, Any])
async def generate_compliance_checklist(request: ComplianceRequest):
    """
    Generiert eine projektspezifische Compliance-Checkliste

    Enthält:
    - Aufgaben vor/bei/nach Installation
    - Kritische Fristen (MaStR!)
    - §14a EnWG Anforderungen
    - Warnungen (Solarspitzengesetz etc.)
    """
    service = get_compliance_service()

    inbetriebnahme = None
    if request.inbetriebnahme_datum:
        try:
            inbetriebnahme = datetime.strptime(request.inbetriebnahme_datum, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Ungültiges Datumsformat. Erwartet: YYYY-MM-DD"
            )

    result = service.generate_project_checklist(
        pv_kwp=request.pv_kwp,
        battery_kwh=request.battery_kwh,
        battery_power_kw=request.battery_power_kw,
        jahresverbrauch_kwh=request.jahresverbrauch_kwh,
        bundesland=request.bundesland,
        inbetriebnahme_datum=inbetriebnahme,
        eeg_typ=request.eeg_typ
    )

    return result


@router.get("/compliance/para-14a")
async def get_para_14a_info(
    battery_power_kw: float = Query(..., gt=0, description="Speicherleistung in kW")
):
    """
    Prüft §14a EnWG Relevanz für einen Speicher

    Speicher > 4,2 kW sind als steuerbare Verbrauchseinrichtungen betroffen.
    """
    service = get_compliance_service()
    return service.get_para_14a_info(battery_power_kw)


@router.get("/compliance/mastr")
async def get_mastr_info():
    """
    Gibt Informationen zur Marktstammdatenregister-Pflicht zurück
    """
    return {
        "pflichten": MASTR_PFLICHTEN,
        "wichtig": "Ohne MaStR-Anmeldung KEIN Anspruch auf EEG-Vergütung!",
        "tipp": "Anmeldung direkt nach Inbetriebnahme, nicht bis zum Fristende warten"
    }


# ============ EEG & TARIF ENDPOINTS ============

@router.get("/eeg/verguetung")
async def get_eeg_verguetung(
    pv_kwp: float = Query(..., gt=0, description="PV-Leistung in kWp"),
    eeg_typ: str = Query("teileinspeisung", description="teileinspeisung oder volleinspeisung")
):
    """
    Berechnet die EEG-Vergütung für eine Anlagengröße

    Berücksichtigt die gestaffelte Vergütung nach Anlagenteilen.
    """
    service = get_compliance_service()
    return service.get_eeg_vergütung(pv_kwp, eeg_typ)


@router.get("/eeg/tarife")
async def get_eeg_tarife():
    """
    Gibt die aktuellen EEG-Vergütungssätze zurück (Stand 08/2025)
    """
    return {
        "tarife": EEG_FEED_IN_TARIFFS,
        "hinweise": [
            "Halbjährliche Degression von 1%",
            "Bei negativen Strompreisen keine Vergütung (Solarspitzengesetz ab 25.02.2025)",
            "Direktvermarktungspflicht ab 100 kWp"
        ]
    }


# ============ FÖRDERUNG ENDPOINTS ============

@router.get("/foerderung/uebersicht")
async def get_foerderung_uebersicht():
    """
    Gibt eine Übersicht aller Förderprogramme zurück
    """
    return {
        "bundesfoerderung": FOERDERUNGEN["bund"],
        "landesfoerderung": FOERDERUNGEN["laender"],
        "wichtig": "Förderantrag IMMER vor Bestellung/Auftragsvergabe stellen!",
        "stand": "Dezember 2025"
    }


@router.get("/foerderung/bundesland/{bundesland}")
async def get_landesfoerderung(bundesland: str):
    """
    Gibt Förderinformationen für ein Bundesland zurück
    """
    bundesland_upper = bundesland.upper()

    if bundesland_upper not in FOERDERUNGEN["laender"]:
        raise HTTPException(
            status_code=404,
            detail=f"Bundesland {bundesland} nicht gefunden. Gültige Kürzel: {list(FOERDERUNGEN['laender'].keys())}"
        )

    return {
        "bundesland": bundesland_upper,
        "foerderung": FOERDERUNGEN["laender"][bundesland_upper],
        "bundesfoerderung": FOERDERUNGEN["bund"],
        "hinweis": "Kommunale Förderungen zusätzlich prüfen!"
    }


# ============ KOSTEN ENDPOINTS ============

@router.post("/kosten/investition", response_model=Dict[str, Any])
async def calculate_investment_costs(request: InvestmentCalcRequest):
    """
    Berechnet die Investitionskosten basierend auf aktuellen Marktpreisen 2025

    Preise sind gestaffelt nach Anlagengröße (Skaleneffekte).
    """
    pv_costs = INVESTMENT_COSTS_2025["pv_cost_per_kwp"]
    battery_costs = INVESTMENT_COSTS_2025["battery_cost_per_kwh"]
    fixed_costs = INVESTMENT_COSTS_2025["fixed_costs"]

    # PV-Kosten (gestaffelt)
    if request.pv_kwp <= 30:
        pv_price = pv_costs["bis_30kwp"]
    elif request.pv_kwp <= 100:
        pv_price = pv_costs["30_100kwp"]
    elif request.pv_kwp <= 500:
        pv_price = pv_costs["100_500kwp"]
    else:
        pv_price = pv_costs["ueber_500kwp"]

    pv_total = request.pv_kwp * pv_price

    # Batterie-Kosten (gestaffelt)
    if request.battery_kwh <= 30:
        battery_price = battery_costs["bis_30kwh"]
    elif request.battery_kwh <= 100:
        battery_price = battery_costs["30_100kwh"]
    elif request.battery_kwh <= 500:
        battery_price = battery_costs["100_500kwh"]
    else:
        battery_price = battery_costs["ueber_500kwh"]

    battery_total = request.battery_kwh * battery_price

    # Fixkosten
    fixed_total = sum(fixed_costs.values())

    # Installation
    installation_total = 0
    if request.include_installation:
        installation_total = (pv_total + battery_total) * INVESTMENT_COSTS_2025["installation_factor"]

    # MwSt-Hinweis
    mwst_befreit = request.pv_kwp <= 30

    total = pv_total + battery_total + fixed_total + installation_total

    return {
        "aufschluesselung": {
            "pv_kosten_eur": round(pv_total, 0),
            "pv_preis_pro_kwp": pv_price,
            "batterie_kosten_eur": round(battery_total, 0),
            "batterie_preis_pro_kwh": battery_price,
            "fixkosten_eur": round(fixed_total, 0),
            "installation_eur": round(installation_total, 0),
        },
        "gesamt_netto_eur": round(total, 0),
        "mwst_befreit": mwst_befreit,
        "mwst_hinweis": "0% MwSt für PV ≤ 30 kWp" if mwst_befreit else "19% MwSt fallen an",
        "gesamt_brutto_eur": round(total if mwst_befreit else total * 1.19, 0),
        "preisbasis": "Dezember 2025"
    }


@router.get("/kosten/referenz")
async def get_cost_reference():
    """
    Gibt die Referenzpreise für Kalkulationen zurück
    """
    return {
        "investitionskosten": INVESTMENT_COSTS_2025,
        "simulation_defaults": SIMULATION_DEFAULTS,
        "hinweis": "Preise sind Richtwerte - regionale Unterschiede möglich"
    }


# ============ NOTSTROM (EMERGENCY POWER) ENDPOINTS ============

@router.post("/notstrom/analyze", response_model=Dict[str, Any])
async def analyze_emergency_power(request: EmergencyPowerAnalysisRequest):
    """
    Analysiert Notstromfähigkeit einer Batterie für kritische Lasten

    Prüft:
    - Ob Leistung für kritische Lasten ausreicht
    - Wie lange Backup-Versorgung möglich ist
    - Empfehlungen für Kapazitätserweiterung
    """
    service = get_emergency_power_service()

    # Backup-Kapazität berechnen
    capacity_requirements = service.calculate_backup_capacity(
        critical_loads_kw=request.critical_loads_kw,
        required_hours=request.required_backup_hours
    )

    # Prüfen ob vorhandene Batterie ausreicht
    capability_check = service.check_backup_capability(
        battery_capacity_kwh=request.battery_capacity_kwh,
        battery_power_kw=request.battery_power_kw,
        critical_loads_kw=request.critical_loads_kw,
        required_hours=request.required_backup_hours,
        current_soc=request.current_soc
    )

    # Szenario-Analyse mit detaillierten Lasten
    critical_loads = [
        {"name": f"Last {i+1}", "power_kw": load, "priority": 1}
        for i, load in enumerate(request.critical_loads_kw)
    ]

    scenarios = service.analyze_emergency_power_scenarios(
        battery_capacity_kwh=request.battery_capacity_kwh,
        battery_power_kw=request.battery_power_kw,
        critical_loads=critical_loads,
        pv_kwp=request.pv_kwp
    )

    return {
        "kapazitaet_anforderungen": capacity_requirements,
        "batterie_pruefung": capability_check,
        "szenarien": scenarios["szenarien"],
        "empfehlung": scenarios["empfehlung"],
        "statistik_deutschland": scenarios["statistik_deutschland"]
    }


@router.post("/notstrom/simulate-blackout", response_model=Dict[str, Any])
async def simulate_blackout(request: BlackoutSimulationRequest):
    """
    Simuliert einen Netzausfall und prüft Notstromversorgung

    Simuliert den Batteriebetrieb während eines definierten Ausfalls:
    - Verbrauch der kritischen Lasten
    - Optionale PV-Unterstützung
    - SOC-Verlauf während des Ausfalls
    """
    service = get_emergency_power_service()

    load_array = np.array(request.load_profile_kw)
    pv_array = np.array(request.pv_profile_kw) if request.pv_profile_kw else None

    if request.outage_start_hour >= len(load_array):
        raise HTTPException(
            status_code=400,
            detail=f"Ausfall-Startstunde ({request.outage_start_hour}) außerhalb des Lastprofils"
        )

    result = service.simulate_blackout(
        load_profile_kw=load_array,
        battery_capacity_kwh=request.battery_capacity_kwh,
        battery_power_kw=request.battery_power_kw,
        critical_loads_kw=request.critical_loads_kw,
        outage_start_hour=request.outage_start_hour,
        outage_duration_hours=request.outage_duration_hours,
        pv_profile_kw=pv_array,
        initial_soc=request.initial_soc,
        interval_minutes=request.interval_minutes
    )

    return result


@router.post("/notstrom/scenarios", response_model=Dict[str, Any])
async def analyze_emergency_scenarios(request: EmergencyScenarioRequest):
    """
    Analysiert verschiedene Notstrom-Szenarien mit benannten kritischen Lasten

    Berechnet Backup-Zeiten für:
    - Alle kritischen Lasten
    - Nur höchste Priorität
    - Mit/ohne PV-Unterstützung
    """
    service = get_emergency_power_service()

    critical_loads = [
        {
            "name": load.name,
            "power_kw": load.power_kw,
            "priority": load.priority
        }
        for load in request.critical_loads
    ]

    result = service.analyze_emergency_power_scenarios(
        battery_capacity_kwh=request.battery_capacity_kwh,
        battery_power_kw=request.battery_power_kw,
        critical_loads=critical_loads,
        pv_kwp=request.pv_kwp
    )

    return result


@router.get("/notstrom/info")
async def get_emergency_power_info():
    """
    Gibt allgemeine Informationen zur Notstromversorgung zurück

    Enthält:
    - Typische kritische Lasten für Gewerbe
    - Ausfallstatistiken Deutschland
    - Planungshinweise
    """
    service = get_emergency_power_service()

    return {
        "typische_kritische_lasten": service.TYPICAL_CRITICAL_LOADS,
        "ausfallstatistik_deutschland": service.OUTAGE_STATISTICS,
        "planungshinweise": [
            "95% aller Stromausfälle in Deutschland dauern weniger als 4 Stunden",
            "Durchschnittliche Ausfalldauer: ca. 12 Minuten pro Jahr (SAIDI)",
            "Für kritische Prozesse: Mindestens 4h Backup empfohlen",
            "Mit PV-Unterstützung kann Backup tagsüber deutlich verlängert werden",
            "Kühllasten und IT-Systeme haben oft höchste Priorität",
            "Notstromfähigkeit ist ein wichtiges Verkaufsargument für Gewerbekunden"
        ],
        "dimensionierung_tipps": [
            "Batterieleistung muss >= Summe kritischer Lasten sein",
            "20% Sicherheitsreserve bei Kapazität einplanen",
            "SOC-Schwelle für Notstrom: 10% (nicht tiefer entladen)",
            "Für längere Ausfälle: PV-Integration berücksichtigen",
            "Lastpriorisierung ermöglicht längere Backup-Zeiten"
        ]
    }


# ============ NETZENTGELT ENDPOINTS ============

# Regionale Netzentgelt-Datenbank (PLZ-basiert)
# Daten basieren auf Bundesnetzagentur-Veröffentlichungen und Netzbetreiber-Preisblättern
NETZENTGELT_REGIONEN = {
    # Format: PLZ-Präfix -> {netzbetreiber, leistungspreis_eur_kw, arbeitspreis_ct_kwh, kategorie}
    # Bayern
    "80": {"netzbetreiber": "SWM Infrastruktur", "leistungspreis": 440, "arbeitspreis": 3.2, "kategorie": "extrem", "region": "München"},
    "81": {"netzbetreiber": "SWM Infrastruktur", "leistungspreis": 440, "arbeitspreis": 3.2, "kategorie": "extrem", "region": "München"},
    "82": {"netzbetreiber": "Bayernwerk", "leistungspreis": 120, "arbeitspreis": 2.8, "kategorie": "hoch", "region": "Oberbayern"},
    "83": {"netzbetreiber": "Bayernwerk", "leistungspreis": 110, "arbeitspreis": 2.7, "kategorie": "mittel", "region": "Oberbayern Süd"},
    "84": {"netzbetreiber": "Bayernwerk", "leistungspreis": 100, "arbeitspreis": 2.6, "kategorie": "mittel", "region": "Niederbayern"},
    "85": {"netzbetreiber": "Bayernwerk", "leistungspreis": 115, "arbeitspreis": 2.8, "kategorie": "hoch", "region": "Oberbayern"},
    "86": {"netzbetreiber": "LEW Verteilnetz", "leistungspreis": 95, "arbeitspreis": 2.5, "kategorie": "mittel", "region": "Schwaben"},
    "87": {"netzbetreiber": "LEW Verteilnetz", "leistungspreis": 90, "arbeitspreis": 2.4, "kategorie": "mittel", "region": "Allgäu"},
    "90": {"netzbetreiber": "N-ERGIE Netz", "leistungspreis": 130, "arbeitspreis": 2.9, "kategorie": "hoch", "region": "Nürnberg"},
    "91": {"netzbetreiber": "N-ERGIE Netz", "leistungspreis": 120, "arbeitspreis": 2.8, "kategorie": "hoch", "region": "Mittelfranken"},
    "93": {"netzbetreiber": "Bayernwerk", "leistungspreis": 85, "arbeitspreis": 2.4, "kategorie": "niedrig", "region": "Oberpfalz"},
    "95": {"netzbetreiber": "Bayernwerk", "leistungspreis": 80, "arbeitspreis": 2.3, "kategorie": "niedrig", "region": "Oberfranken"},
    "97": {"netzbetreiber": "Bayernwerk", "leistungspreis": 90, "arbeitspreis": 2.5, "kategorie": "mittel", "region": "Unterfranken"},

    # Baden-Württemberg
    "70": {"netzbetreiber": "Netze BW", "leistungspreis": 145, "arbeitspreis": 3.0, "kategorie": "sehr_hoch", "region": "Stuttgart"},
    "71": {"netzbetreiber": "Netze BW", "leistungspreis": 130, "arbeitspreis": 2.9, "kategorie": "hoch", "region": "Region Stuttgart"},
    "72": {"netzbetreiber": "Netze BW", "leistungspreis": 110, "arbeitspreis": 2.7, "kategorie": "hoch", "region": "Reutlingen/Tübingen"},
    "73": {"netzbetreiber": "Netze BW", "leistungspreis": 105, "arbeitspreis": 2.6, "kategorie": "mittel", "region": "Göppingen"},
    "74": {"netzbetreiber": "Netze BW", "leistungspreis": 100, "arbeitspreis": 2.5, "kategorie": "mittel", "region": "Heilbronn"},
    "75": {"netzbetreiber": "Netze BW", "leistungspreis": 95, "arbeitspreis": 2.5, "kategorie": "mittel", "region": "Pforzheim"},
    "76": {"netzbetreiber": "Netze BW", "leistungspreis": 120, "arbeitspreis": 2.8, "kategorie": "hoch", "region": "Karlsruhe"},
    "77": {"netzbetreiber": "Netze BW", "leistungspreis": 90, "arbeitspreis": 2.4, "kategorie": "mittel", "region": "Offenburg"},
    "78": {"netzbetreiber": "Netze BW", "leistungspreis": 85, "arbeitspreis": 2.3, "kategorie": "niedrig", "region": "Villingen-Schwenningen"},
    "79": {"netzbetreiber": "Netze BW", "leistungspreis": 100, "arbeitspreis": 2.5, "kategorie": "mittel", "region": "Freiburg"},

    # Nordrhein-Westfalen
    "40": {"netzbetreiber": "Netzgesellschaft Düsseldorf", "leistungspreis": 160, "arbeitspreis": 3.1, "kategorie": "sehr_hoch", "region": "Düsseldorf"},
    "41": {"netzbetreiber": "Westnetz", "leistungspreis": 110, "arbeitspreis": 2.7, "kategorie": "hoch", "region": "Mönchengladbach"},
    "42": {"netzbetreiber": "WSW Netz", "leistungspreis": 135, "arbeitspreis": 2.9, "kategorie": "hoch", "region": "Wuppertal"},
    "44": {"netzbetreiber": "Westnetz", "leistungspreis": 105, "arbeitspreis": 2.6, "kategorie": "mittel", "region": "Dortmund"},
    "45": {"netzbetreiber": "Westnetz", "leistungspreis": 115, "arbeitspreis": 2.7, "kategorie": "hoch", "region": "Essen"},
    "46": {"netzbetreiber": "Westnetz", "leistungspreis": 100, "arbeitspreis": 2.5, "kategorie": "mittel", "region": "Oberhausen"},
    "47": {"netzbetreiber": "Westnetz", "leistungspreis": 110, "arbeitspreis": 2.7, "kategorie": "hoch", "region": "Duisburg"},
    "48": {"netzbetreiber": "Westnetz", "leistungspreis": 85, "arbeitspreis": 2.3, "kategorie": "niedrig", "region": "Münster"},
    "50": {"netzbetreiber": "RheinEnergie", "leistungspreis": 155, "arbeitspreis": 3.0, "kategorie": "sehr_hoch", "region": "Köln"},
    "51": {"netzbetreiber": "RheinEnergie", "leistungspreis": 140, "arbeitspreis": 2.9, "kategorie": "hoch", "region": "Köln Umland"},
    "53": {"netzbetreiber": "Westnetz", "leistungspreis": 125, "arbeitspreis": 2.8, "kategorie": "hoch", "region": "Bonn"},

    # Berlin
    "10": {"netzbetreiber": "Stromnetz Berlin", "leistungspreis": 180, "arbeitspreis": 3.3, "kategorie": "sehr_hoch", "region": "Berlin Mitte"},
    "12": {"netzbetreiber": "Stromnetz Berlin", "leistungspreis": 180, "arbeitspreis": 3.3, "kategorie": "sehr_hoch", "region": "Berlin"},
    "13": {"netzbetreiber": "Stromnetz Berlin", "leistungspreis": 180, "arbeitspreis": 3.3, "kategorie": "sehr_hoch", "region": "Berlin"},
    "14": {"netzbetreiber": "E.DIS Netz", "leistungspreis": 95, "arbeitspreis": 2.5, "kategorie": "mittel", "region": "Brandenburg"},

    # Hamburg
    "20": {"netzbetreiber": "Stromnetz Hamburg", "leistungspreis": 165, "arbeitspreis": 3.2, "kategorie": "sehr_hoch", "region": "Hamburg"},
    "21": {"netzbetreiber": "Stromnetz Hamburg", "leistungspreis": 165, "arbeitspreis": 3.2, "kategorie": "sehr_hoch", "region": "Hamburg"},
    "22": {"netzbetreiber": "Stromnetz Hamburg", "leistungspreis": 165, "arbeitspreis": 3.2, "kategorie": "sehr_hoch", "region": "Hamburg"},

    # Hessen
    "60": {"netzbetreiber": "Mainova", "leistungspreis": 170, "arbeitspreis": 3.2, "kategorie": "sehr_hoch", "region": "Frankfurt"},
    "61": {"netzbetreiber": "Mainova", "leistungspreis": 150, "arbeitspreis": 3.0, "kategorie": "sehr_hoch", "region": "Frankfurt Umland"},
    "63": {"netzbetreiber": "Syna", "leistungspreis": 105, "arbeitspreis": 2.6, "kategorie": "mittel", "region": "Hanau"},
    "64": {"netzbetreiber": "Entega Netz", "leistungspreis": 115, "arbeitspreis": 2.7, "kategorie": "hoch", "region": "Darmstadt"},
    "65": {"netzbetreiber": "Syna", "leistungspreis": 130, "arbeitspreis": 2.8, "kategorie": "hoch", "region": "Wiesbaden"},

    # Niedersachsen
    "30": {"netzbetreiber": "Avacon Netz", "leistungspreis": 105, "arbeitspreis": 2.6, "kategorie": "mittel", "region": "Hannover"},
    "31": {"netzbetreiber": "Avacon Netz", "leistungspreis": 90, "arbeitspreis": 2.4, "kategorie": "mittel", "region": "Celle"},
    "26": {"netzbetreiber": "EWE Netz", "leistungspreis": 75, "arbeitspreis": 2.2, "kategorie": "niedrig", "region": "Oldenburg"},
    "27": {"netzbetreiber": "EWE Netz", "leistungspreis": 70, "arbeitspreis": 2.1, "kategorie": "niedrig", "region": "Cuxhaven"},
    "28": {"netzbetreiber": "wesernetz", "leistungspreis": 120, "arbeitspreis": 2.8, "kategorie": "hoch", "region": "Bremen"},
    "29": {"netzbetreiber": "Avacon Netz", "leistungspreis": 65, "arbeitspreis": 2.0, "kategorie": "niedrig", "region": "Uelzen"},
    "38": {"netzbetreiber": "Avacon Netz", "leistungspreis": 80, "arbeitspreis": 2.3, "kategorie": "niedrig", "region": "Braunschweig"},

    # Sachsen
    "01": {"netzbetreiber": "SachsenNetze", "leistungspreis": 95, "arbeitspreis": 2.5, "kategorie": "mittel", "region": "Dresden"},
    "04": {"netzbetreiber": "Netz Leipzig", "leistungspreis": 110, "arbeitspreis": 2.7, "kategorie": "hoch", "region": "Leipzig"},
    "09": {"netzbetreiber": "Mitnetz Strom", "leistungspreis": 75, "arbeitspreis": 2.2, "kategorie": "niedrig", "region": "Chemnitz"},

    # Schleswig-Holstein
    "24": {"netzbetreiber": "SH Netz", "leistungspreis": 85, "arbeitspreis": 2.3, "kategorie": "niedrig", "region": "Kiel"},
    "25": {"netzbetreiber": "SH Netz", "leistungspreis": 70, "arbeitspreis": 2.1, "kategorie": "niedrig", "region": "Westküste"},

    # Mecklenburg-Vorpommern
    "18": {"netzbetreiber": "E.DIS Netz", "leistungspreis": 65, "arbeitspreis": 2.0, "kategorie": "niedrig", "region": "Rostock"},
    "19": {"netzbetreiber": "WEMAG Netz", "leistungspreis": 60, "arbeitspreis": 1.9, "kategorie": "niedrig", "region": "Schwerin"},
}

# Fallback für nicht gefundene PLZ
NETZENTGELT_DEFAULT = {
    "netzbetreiber": "Unbekannt",
    "leistungspreis": 100,  # Bundesdurchschnitt
    "arbeitspreis": 2.5,
    "kategorie": "mittel",
    "region": "Deutschland (Durchschnitt)"
}


@router.get("/netzentgelt/plz/{plz}")
async def get_netzentgelt_by_plz(plz: str):
    """
    Gibt Netzentgelt-Informationen für eine PLZ zurück

    Basiert auf veröffentlichten Preisblättern der Netzbetreiber.
    Die Daten sind Richtwerte - exakte Preise beim Netzbetreiber erfragen.
    """
    if not plz or len(plz) < 2:
        raise HTTPException(
            status_code=400,
            detail="PLZ muss mindestens 2 Stellen haben"
        )

    # Suche nach PLZ-Präfix (2-stellig)
    plz_prefix = plz[:2]

    if plz_prefix in NETZENTGELT_REGIONEN:
        data = NETZENTGELT_REGIONEN[plz_prefix]
        found = True
    else:
        data = NETZENTGELT_DEFAULT
        found = False

    # Peak-Shaving Potenzial berechnen
    leistungspreis = data["leistungspreis"]
    peak_shaving_attraktiv = leistungspreis >= 100

    return {
        "plz": plz,
        "gefunden": found,
        "netzentgelt": {
            "netzbetreiber": data["netzbetreiber"],
            "region": data["region"],
            "leistungspreis_eur_kw_jahr": leistungspreis,
            "arbeitspreis_ct_kwh": data["arbeitspreis"],
            "kategorie": data["kategorie"],
        },
        "peak_shaving": {
            "attraktiv": peak_shaving_attraktiv,
            "ersparnis_bei_10kw_reduktion_eur": leistungspreis * 10,
            "ersparnis_bei_50kw_reduktion_eur": leistungspreis * 50,
            "ersparnis_bei_100kw_reduktion_eur": leistungspreis * 100,
        },
        "hinweise": [
            "Leistungspreis gilt für RLM-Messung (>100.000 kWh/Jahr)",
            "Preise sind Richtwerte aus Preisblättern der Netzbetreiber",
            "Exakte Werte beim zuständigen Netzbetreiber erfragen"
        ] if found else [
            "PLZ nicht in Datenbank gefunden",
            "Bundesdurchschnitt wird angezeigt",
            "Netzbetreiber direkt kontaktieren für exakte Preise"
        ]
    }


@router.get("/netzentgelt/kategorien")
async def get_netzentgelt_kategorien():
    """
    Gibt die Netzentgelt-Kategorien mit Erläuterungen zurück
    """
    return {
        "kategorien": {
            "niedrig": {
                "bereich_eur_kw": "60-80",
                "beschreibung": "Ländliche Gebiete, gut ausgebaute Netze",
                "beispiele": ["Norddeutschland", "Ostdeutschland ländlich", "Allgäu"]
            },
            "mittel": {
                "bereich_eur_kw": "80-120",
                "beschreibung": "Durchschnitt Deutschland, mittelgroße Städte",
                "beispiele": ["Mittelfränkische Städte", "Schwaben", "Rheinland-Pfalz"]
            },
            "hoch": {
                "bereich_eur_kw": "120-150",
                "beschreibung": "Größere Städte und Ballungsräume",
                "beispiele": ["Köln Umland", "Nürnberg", "Hannover"]
            },
            "sehr_hoch": {
                "bereich_eur_kw": "150-200",
                "beschreibung": "Großstädte mit hoher Netzdichte",
                "beispiele": ["Berlin", "Hamburg", "Frankfurt", "Stuttgart"]
            },
            "extrem": {
                "bereich_eur_kw": "200-450",
                "beschreibung": "Spitzennetze mit sehr hoher Auslastung",
                "beispiele": ["München (SWM)", "Einzelne Industriegebiete"]
            }
        },
        "peak_shaving_empfehlung": {
            "ab_kategorie": "mittel",
            "begruendung": "Ab 100 €/kW/Jahr wird Peak-Shaving wirtschaftlich interessant",
            "amortisation_grob": "Bei Reduktion um 50 kW: ~5.000-22.500 €/Jahr Ersparnis"
        }
    }


@router.get("/netzentgelt/statistik")
async def get_netzentgelt_statistik():
    """
    Gibt Statistiken zur Netzentgelt-Datenbank zurück
    """
    kategorien_count = {}
    total_leistungspreis = 0
    count = 0

    for data in NETZENTGELT_REGIONEN.values():
        kat = data["kategorie"]
        kategorien_count[kat] = kategorien_count.get(kat, 0) + 1
        total_leistungspreis += data["leistungspreis"]
        count += 1

    return {
        "anzahl_regionen": count,
        "verteilung_kategorien": kategorien_count,
        "durchschnitt_leistungspreis": round(total_leistungspreis / count, 0) if count > 0 else 0,
        "spanne": {
            "minimum_eur_kw": min(d["leistungspreis"] for d in NETZENTGELT_REGIONEN.values()),
            "maximum_eur_kw": max(d["leistungspreis"] for d in NETZENTGELT_REGIONEN.values()),
        },
        "datenstand": "Dezember 2025",
        "quelle": "Bundesnetzagentur Preisblattauswertung"
    }
