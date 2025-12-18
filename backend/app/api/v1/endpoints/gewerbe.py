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
from app.config import (
    EEG_FEED_IN_TARIFFS,
    INVESTMENT_COSTS_2025,
    LEISTUNGSPREISE_EUR_KW_JAHR,
    FOERDERUNGEN,
    PARA_14A_ENWG,
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
