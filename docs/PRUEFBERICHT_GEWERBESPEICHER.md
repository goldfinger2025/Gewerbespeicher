# Prüfbericht: Gewerbespeicher Berechnungsmodelle

**Datum:** 2025-12-18
**Prüfer:** Claude Code Review
**Version:** 1.0

---

## Inhaltsverzeichnis

1. [Executive Summary](#1-executive-summary)
2. [Qualitätsprüfung der Berechnungslogik](#2-qualitätsprüfung-der-berechnungslogik)
3. [Gesetzliche Anforderungen (Stand 2025)](#3-gesetzliche-anforderungen-stand-2025)
4. [Förderprogramme](#4-förderprogramme)
5. [Identifizierte Lücken](#5-identifizierte-lücken)
6. [Verbesserungsvorschläge](#6-verbesserungsvorschläge)
7. [Prioritäten für die Implementierung](#7-prioritäten-für-die-implementierung)

---

## 1. Executive Summary

Die Gewerbespeicher-Anwendung bietet eine **solide technische Basis** für die Planung von PV-Speichersystemen. Die Kernberechnungen (Energieflüsse, Autarkie, Eigenverbrauch) sind **fachlich korrekt** implementiert.

Jedoch wurden **mehrere kritische Lücken** identifiziert, die für einen erfolgreichen Einsatz im Gewerbebereich geschlossen werden sollten:

### Stärken ✅
- Professionelle pvlib-Integration mit realen PVGIS-Wetterdaten
- Korrekte Energieflussberechnung mit Batterieeffizienz (95%)
- Sinnvolle Lastprofile für 4 Gewerbetypen
- NPV/IRR-Berechnungen vorhanden
- KI-gestützte Dimensionierung

### Kritische Lücken ❌
- **Keine Peak-Shaving-Berechnung** (wichtigster ROI-Faktor für Gewerbe!)
- **Keine Leistungspreis-Berücksichtigung** bei Netzentgelten
- **Veraltete Preiskonstanten** (2024 statt 2025)
- **Fehlende EEG-2025-Regelungen** (negative Strompreise, Degression)
- **Keine Förderungsinformationen** für Installateure
- **Keine §14a EnWG-Hinweise** für steuerbare Verbrauchseinrichtungen

---

## 2. Qualitätsprüfung der Berechnungslogik

### 2.1 PV-Ertragssimulation (`pvlib_simulator.py`)

| Aspekt | Status | Bewertung |
|--------|--------|-----------|
| pvlib-Integration | ✅ Korrekt | Professionelle Bibliothek |
| PVGIS TMY-Daten | ✅ Korrekt | Echte Wetterdaten, 30-Tage-Cache |
| Temperaturkoeffizient | ✅ Korrekt | -0.4%/°C implementiert |
| Systemverluste | ⚠️ Vereinfacht | Performance Ratio nur implizit |
| Jahresertrag | ✅ Realistisch | ~950 kWh/kWp für Nord-DE |

**Empfohlene Erweiterung:** Expliziter Performance Ratio (0.80-0.85) als Parameter

### 2.2 Lastprofile

| Profiltyp | Implementierung | Realitätsnähe |
|-----------|-----------------|---------------|
| Büro | ✅ | Sehr gut - Mo-Fr 8-18 Uhr |
| Einzelhandel | ✅ | Gut - längere Öffnungszeiten |
| Produktion | ✅ | Gut - Schichtbetrieb andeutbar |
| Lager/Logistik | ✅ | Gut - früher Start |

**Problem:** Keine Möglichkeit für Lastspitzen-Events (Maschinenanläufe etc.)

### 2.3 Batteriesimulation

```python
# Aktuell implementiert (korrekt):
charge_efficiency = 0.95
discharge_efficiency = 0.95
min_soc = battery_kwh * 0.1   # 10% Minimum
max_soc = battery_kwh * 0.9   # 90% Maximum
```

| Aspekt | Status | Kommentar |
|--------|--------|-----------|
| Round-Trip-Efficiency | ✅ ~90% | Realistisch für LFP |
| SOC-Grenzen | ✅ 10-90% | Gute Praxis |
| Zyklenberechnung | ✅ Korrekt | Entladung/Kapazität |
| Kalendarische Alterung | ❌ Fehlt | Sollte hinzugefügt werden |
| Zyklus-Degradation | ⚠️ Vereinfacht | Nur 0.5%/Jahr pauschal |

### 2.4 Finanzberechnungen

| Berechnung | Formel | Status |
|------------|--------|--------|
| Jährliche Einsparung | `(Verbrauch × Strompreis) - (Netzbezug × Strompreis - Export × EEG)` | ✅ Korrekt |
| Amortisation | `Investition / Einsparung` | ✅ Korrekt |
| NPV | 20 Jahre, 3% Diskont, 0.5% Degradation | ✅ Sinnvoll |
| IRR | `(Einsparung / Investition) × 100` | ⚠️ Vereinfacht |

**Kritisches Problem:**
```python
# AKTUELL (pvlib_simulator.py, Zeile 495-502):
pv_cost_per_kwp = 1100      # €/kWp
battery_cost_per_kwh = 600  # €/kWh
fixed_costs = 2000          # €

# Diese Preise sind für 2024/2025 Gewerbe zu niedrig!
```

### 2.5 Fehlende Berechnungen

| Feature | Priorität | Business Impact |
|---------|-----------|-----------------|
| **Peak-Shaving / Leistungspreis** | 🔴 KRITISCH | Hauptargument für Gewerbespeicher! |
| **15-Minuten-Lastspitzenanalyse** | 🔴 KRITISCH | Grundlage für Leistungspreis |
| **Dynamische Stromtarife** | 🟡 HOCH | Zunehmend relevant |
| **Notstromfähigkeit** | 🟡 HOCH | Verkaufsargument |
| **Netzentgelt-Module (§14a)** | 🟡 HOCH | 60% Ersparnis möglich |

---

## 3. Gesetzliche Anforderungen (Stand 2025)

### 3.1 EEG 2025 - Einspeisevergütung

| Anlagengröße | Teileinspeisung | Volleinspeisung | Gültig ab |
|--------------|-----------------|-----------------|-----------|
| ≤ 10 kWp | 7,86 ct/kWh | 12,47 ct/kWh | 01.08.2025 |
| 10-40 kWp | 6,80 ct/kWh | 10,45 ct/kWh | 01.08.2025 |
| > 40 kWp | +1,5 ct (Solarpaket I, ausstehend) | | |

**WICHTIGE ÄNDERUNGEN 2025:**
1. **Halbjährliche Degression:** -1% alle 6 Monate (seit 31.01.2024)
2. **Solarspitzengesetz (25.02.2025):** Keine Vergütung bei negativen Strompreisen
3. **Direktvermarktungspflicht:** Stufenweise Absenkung auf 25 kW bis 2027
4. **ZEREZ-Pflicht:** Registrierung im Zentralregister ab 02/2025

### 3.2 Marktstammdatenregister

**Pflichten:**
- Registrierung innerhalb 1 Monat nach Inbetriebnahme
- Speicher UND PV-Anlage separat anmelden
- Datenpflege bei Änderungen
- **Sanktion bei Verstoß:** Verlust der EEG-Vergütung!

### 3.3 §14a EnWG - Steuerbare Verbrauchseinrichtungen

**Betrifft Speicher > 4,2 kW Ladeleistung:**

| Modul | Ersparnis | Voraussetzung |
|-------|-----------|---------------|
| Modul 1 (Pauschale) | 110-190 €/Jahr | Standard |
| Modul 2 (Prozentual) | 60% Netzentgelt-Rabatt | Separater Zähler |
| Modul 3 (Zeitvariabel) | Variabel | Smart Meter, ab 04/2025 |

### 3.4 Netzanschluss & Leistungsmessung

**Ab 100.000 kWh/Jahr Verbrauch:**
- 15-Minuten-Leistungsmessung (RLM)
- Leistungspreis: **60-440 €/kW** (regionsabhängig)
- Höchste Lastspitze im Jahr = Basis für Jahreskosten!

---

## 4. Förderprogramme

### 4.1 Bundesförderung

| Programm | Art | Details |
|----------|-----|---------|
| **KfW 270** | Kredit | Bis 100% Finanzierung, ab 3,66% eff. Zins |
| MwSt-Befreiung | Steuer | 0% MwSt auf PV + Speicher ≤ 30 kWp |
| BAFA Energieberatung | Zuschuss | Beratungskosten förderbar |

### 4.2 Landesförderungen (aktiv Stand 12/2025)

| Bundesland | Programm | Förderung |
|------------|----------|-----------|
| Baden-Württemberg | Netzdienliche Speicher | Zuschuss pro kWh |
| Berlin | Stromspeicher-Programm | Direkte Förderung |
| Hessen | WIBank Darlehen | Zinszuschuss |
| Sachsen-Anhalt | Speicher > 30 kWh | Investitionszuschuss |

### 4.3 Kommunale Programme

Viele Städte und Kommunen bieten eigene Förderprogramme - **lokale Recherche empfohlen!**

---

## 5. Identifizierte Lücken

### 5.1 KRITISCH - Sofort beheben

| # | Lücke | Impact | Aufwand |
|---|-------|--------|---------|
| 1 | **Keine Peak-Shaving-Berechnung** | Hauptargument für Gewerbekunden fehlt | Hoch |
| 2 | **Keine Leistungspreis-Berücksichtigung** | Einsparungspotenzial wird unterschätzt | Mittel |
| 3 | **Veraltete Einspeisevergütung** (8 ct fest) | Sollte aktuell sein | Niedrig |
| 4 | **Keine EEG-Degression** | Vergütung zu hoch angegeben | Niedrig |

### 5.2 HOCH - Zeitnah implementieren

| # | Lücke | Impact |
|---|-------|--------|
| 5 | Keine Förderungsübersicht für Installateure | Verkaufsargument fehlt |
| 6 | Keine §14a EnWG-Informationen | Gesetzespflicht nicht erklärt |
| 7 | Keine MaStR-Checkliste | Kunde könnte Vergütung verlieren |
| 8 | Keine Notstromfunktions-Berechnung | USV-Kapazität wichtig |
| 9 | Keine dynamischen Stromtarife | Zukunftsrelevant |

### 5.3 MITTEL - Mittelfristig ergänzen

| # | Lücke |
|---|-------|
| 10 | Keine regionale Netzentgelt-Datenbank |
| 11 | Keine Batteriedegradationsmodelle (kalendarisch + zyklisch) |
| 12 | Keine CO2-Bilanz mit aktuellem Strommix |
| 13 | Keine Flexibilitätsvermarktung (Regelenergie) |

---

## 6. Verbesserungsvorschläge

### 6.1 Peak-Shaving-Modul (KRITISCH)

**Neuer Service: `peak_shaving_service.py`**

```python
class PeakShavingAnalyzer:
    """
    Analysiert Lastspitzen und berechnet Einsparpotenzial
    durch Gewerbespeicher-Einsatz
    """

    def analyze_load_peaks(
        self,
        load_profile_15min: np.ndarray,  # 15-Min-Auflösung!
        leistungspreis_eur_kw: float = 100.0
    ) -> Dict:
        """
        Identifiziert die Top-10 Lastspitzen
        Berechnet mögliche Reduktion durch Speicher
        """
        pass

    def calculate_peak_shaving_roi(
        self,
        battery_kwh: float,
        battery_power_kw: float,
        current_peak_kw: float,
        target_peak_kw: float,
        leistungspreis: float
    ) -> Dict:
        """
        ROI durch Peak-Shaving berechnen

        Beispiel:
        - Aktuelle Spitze: 800 kW
        - Zielspitze: 500 kW (Reduktion 300 kW)
        - Leistungspreis: 100 €/kW/Jahr
        - Ersparnis: 30.000 €/Jahr !
        """
        peak_reduction_kw = current_peak_kw - target_peak_kw
        annual_savings = peak_reduction_kw * leistungspreis
        return {
            "peak_reduction_kw": peak_reduction_kw,
            "annual_leistungspreis_savings_eur": annual_savings
        }
```

### 6.2 Aktualisierte Preiskonstanten

```python
# config.py - AKTUALISIEREN auf 2025

# Einspeisevergütung (Stand 08/2025, halbjährlich prüfen!)
EEG_FEED_IN_TARIFFS = {
    "teileinspeisung": {
        "bis_10kwp": 0.0786,    # 7,86 ct/kWh
        "10_40kwp": 0.0680,     # 6,80 ct/kWh
        "ueber_40kwp": 0.0680,  # Solarpaket I ausstehend
    },
    "volleinspeisung": {
        "bis_10kwp": 0.1247,
        "10_40kwp": 0.1045,
    },
    "degression_halbjahr": 0.01,  # -1% alle 6 Monate
    "naechste_degression": "2026-02-01"
}

# Investitionskosten 2025 (Gewerbe, inkl. Installation)
INVESTMENT_COSTS = {
    "pv_cost_per_kwp": {
        "bis_30kwp": 1200,      # €/kWp
        "30_100kwp": 1050,      # Größenrabatt
        "ueber_100kwp": 950,
    },
    "battery_cost_per_kwh": {
        "bis_50kwh": 650,
        "50_200kwh": 550,
        "ueber_200kwh": 480,
    },
    "fixed_costs_base": 3000,  # Planung, Anmeldung
    "installation_percent": 0.12,  # 12% der Komponentenkosten
}

# Leistungspreise (regional sehr unterschiedlich!)
LEISTUNGSPREISE_RANGES = {
    "niedrig": 60,   # €/kW/Jahr (ländlich)
    "mittel": 120,   # €/kW/Jahr (städtisch)
    "hoch": 200,     # €/kW/Jahr (Ballungsraum)
    "sehr_hoch": 440 # €/kW/Jahr (Spitzennetze)
}
```

### 6.3 Förderungs-Infomodul für Installateure

```python
# services/foerderung_service.py

class FoerderungService:
    """
    Informiert Installateure über verfügbare Förderungen
    """

    BUNDESFOERDERUNG = {
        "kfw_270": {
            "name": "KfW 270 - Erneuerbare Energien Standard",
            "art": "Zinsgünstiger Kredit",
            "max_finanzierung": "100%",
            "laufzeit": "5-30 Jahre",
            "effektivzins_ab": 3.66,
            "antragstellung": "Vor Bestellung bei Hausbank",
            "url": "https://www.kfw.de/270"
        },
        "mwst_befreiung": {
            "name": "Mehrwertsteuerbefreiung",
            "art": "Steuerersparnis",
            "bedingung": "PV ≤ 30 kWp",
            "ersparnis": "19% auf Anschaffung + Installation",
            "automatisch": True
        }
    }

    LANDESFOERDERUNGEN = {
        "BW": {"aktiv": True, "programm": "Netzdienliche PV-Speicher"},
        "BE": {"aktiv": True, "programm": "Stromspeicher-Programm"},
        "HE": {"aktiv": True, "programm": "WIBank Darlehen"},
        "ST": {"aktiv": True, "programm": "Speicher > 30 kWh"},
        # ... weitere Bundesländer
    }

    def get_applicable_subsidies(
        self,
        bundesland: str,
        pv_kwp: float,
        battery_kwh: float,
        is_gewerbe: bool = True
    ) -> List[Dict]:
        """
        Gibt alle anwendbaren Förderungen zurück
        """
        pass
```

### 6.4 Compliance-Checkliste für Installateure

```python
# services/compliance_service.py

class ComplianceService:
    """
    Generiert Checklisten für gesetzliche Anforderungen
    """

    def generate_checklist(
        self,
        pv_kwp: float,
        battery_kwh: float,
        battery_power_kw: float,
        jahresverbrauch_kwh: float
    ) -> Dict:
        """
        Erzeugt projektspezifische Checkliste
        """
        checklist = {
            "vor_installation": [],
            "bei_installation": [],
            "nach_installation": [],
            "laufend": []
        }

        # MaStR-Registrierung (PFLICHT)
        checklist["nach_installation"].append({
            "task": "Marktstammdatenregister-Anmeldung",
            "frist": "1 Monat nach Inbetriebnahme",
            "url": "https://www.marktstammdatenregister.de",
            "wichtig": "Ohne Anmeldung KEINE EEG-Vergütung!",
            "benoetigte_daten": [
                "Installierte PV-Leistung (kWp)",
                "Speicherkapazität (kWh)",
                "Netzbetreiber",
                "Inbetriebnahmedatum"
            ]
        })

        # §14a EnWG (wenn Speicher > 4,2 kW)
        if battery_power_kw > 4.2:
            checklist["bei_installation"].append({
                "task": "§14a EnWG - Steuerbare Verbrauchseinrichtung",
                "pflicht": True,
                "info": "Speicher muss netzdienlich steuerbar sein",
                "vorteil": "Netzentgelt-Reduktion bis 60% möglich",
                "module": ["Modul 1 (Pauschale)", "Modul 2 (60% Rabatt)"]
            })

        # Direktvermarktungspflicht
        if pv_kwp > 25:
            checklist["vor_installation"].append({
                "task": "Direktvermarktung prüfen",
                "info": f"Ab 25 kWp Pflicht (ab 2026 stufenweise)",
                "aktuell_pflicht": pv_kwp > 100
            })

        # ZEREZ-Registrierung (NEU ab 02/2025)
        checklist["nach_installation"].append({
            "task": "ZEREZ-Registrierung",
            "frist": "Bei Inbetriebnahme",
            "info": "Zentralregister für Einheiten- und Komponentenzertifikate",
            "neu_ab": "Februar 2025"
        })

        return checklist
```

### 6.5 Erweiterte Wirtschaftlichkeitsberechnung

```python
# In pvlib_simulator.py erweitern:

async def simulate_year_extended(
    self,
    # ... bisherige Parameter ...

    # NEU: Gewerbe-spezifische Parameter
    jahresverbrauch_kwh: float = 100000,  # > 100.000 = RLM-Messung
    leistungspreis_eur_kw: float = 100.0,
    aktuelle_lastspitze_kw: float = None,
    netzentgelt_arbeitspreis: float = 0.08,  # ct/kWh
    §14a_modul: str = None,  # "modul1" | "modul2" | None
) -> Dict:
    """
    Erweiterte Simulation mit Peak-Shaving und Leistungspreis
    """
    # ... bisherige Berechnung ...

    # NEU: Peak-Shaving-Berechnung
    if jahresverbrauch_kwh >= 100000 and aktuelle_lastspitze_kw:
        peak_shaving_result = self._calculate_peak_shaving(
            load_profile_15min,
            battery_kwh,
            battery_power_kw,
            aktuelle_lastspitze_kw,
            leistungspreis_eur_kw
        )

        results["peak_shaving"] = peak_shaving_result
        results["annual_savings_eur"] += peak_shaving_result["savings_eur"]

    # NEU: §14a-Ersparnis
    if §14a_modul == "modul1":
        results["§14a_ersparnis_eur"] = 150  # Durchschnitt
    elif §14a_modul == "modul2":
        results["§14a_ersparnis_eur"] = netzentgelt_arbeitspreis * 0.6 * total_grid_import

    return results
```

---

## 7. Prioritäten für die Implementierung

### Phase 1: Sofort (1-2 Wochen)
1. ✅ Einspeisevergütung aktualisieren (7,86 ct/kWh)
2. ✅ Investitionskosten-Konstanten anpassen
3. ✅ EEG-Degression implementieren
4. ✅ MaStR-Checkliste hinzufügen

### Phase 2: Kurzfristig (2-4 Wochen)
5. 🔲 Peak-Shaving-Modul implementieren
6. 🔲 Leistungspreis-Berechnung hinzufügen
7. 🔲 §14a EnWG-Informationen integrieren
8. 🔲 Förderungs-Übersicht erstellen

### Phase 3: Mittelfristig (1-2 Monate)
9. 🔲 Dynamische Stromtarife
10. 🔲 Notstrom-Kapazitätsberechnung
11. 🔲 Regionale Netzentgelt-Datenbank
12. 🔲 Erweiterte Degradationsmodelle

### Phase 4: Langfristig (3+ Monate)
13. 🔲 Flexibilitätsvermarktung (Regelenergie)
14. 🔲 Automatische Förderungsdatenbank
15. 🔲 CO2-Bilanzierung mit aktuellem Strommix

---

## Quellen

- [KfW Programm 270 - Erneuerbare Energien Standard](https://www.kfw.de/270)
- [Bundesnetzagentur - EEG-Fördersätze](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/ErneuerbareEnergien/EEG_Foerderung/start.html)
- [Marktstammdatenregister](https://www.marktstammdatenregister.de)
- [§14a EnWG - Steuerbare Verbrauchseinrichtungen](https://www.bundesnetzagentur.de/DE/Beschlusskammern/BK06/BK6_83_Zug_Mess/841_SteuVE/BK6_SteuVE_node.html)
- [pv magazine - Wann Gewerbespeicher sinnvoll sind](https://www.pv-magazine.de/2025/11/11/wichtige-indikatoren-im-ueberblick-wann-gewerbespeicher-sinnvoll-sind/)
- [Finanztip - Einspeisevergütung 2025](https://www.finanztip.de/photovoltaik/einspeiseverguetung/)
- [Verbraucherzentrale - EEG 2023/24](https://www.verbraucherzentrale.de/wissen/energie/erneuerbare-energien/eeg-202324-was-heute-fuer-photovoltaikanlagen-gilt-75401)

---

*Dieser Bericht dient als Grundlage für die Weiterentwicklung der Gewerbespeicher-Anwendung.*
