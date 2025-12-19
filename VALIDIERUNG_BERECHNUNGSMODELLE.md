# Validierung der Berechnungsmodelle - Gewerbespeicher-Anwendung

**Datum:** 19. Dezember 2025
**Status:** Validierung abgeschlossen, kritische Korrekturen durchgeführt

---

## Zusammenfassung

Die Anwendung wurde einer umfassenden Validierung unterzogen. Es wurden **2 kritische Fehler** identifiziert und korrigiert, sowie mehrere Verbesserungsvorschläge dokumentiert.

### Korrigierte Fehler:
1. ✅ **IRR-Berechnung** war fehlerhaft (einfache Rendite statt echte IRR)
2. ✅ **CO2-Emissionsfaktor** war veraltet (0.380 → 0.363 kg CO2/kWh)

---

## 1. PV-Simulator (pvlib_simulator.py)

### Status: ✅ VALIDE

**Verwendete Methodik:**
- pvlib-Bibliothek für physikalisch korrekte PV-Modellierung
- PVGIS TMY (Typical Meteorological Year) Wetterdaten vom EU JRC
- Modelchain mit `aoi_model='physical'` und `spectral_model='no_loss'`

**Geprüfte Parameter:**
| Parameter | Wert | Validierung |
|-----------|------|-------------|
| Temperaturkoeffizient | -0.004 %/°C | ✅ Standard für monokristalline Module |
| Wechselrichter-Effizienz | 96% | ✅ Typisch für moderne Geräte |
| Systemdegradation | 0.5%/Jahr | ✅ Konservativ, Hersteller geben 0.4-0.5% an |

**Lastprofile:**
- Office, Retail, Production, Warehouse Profile implementiert
- Saisonale Variation (±15%) berücksichtigt
- Wochenend-Faktoren pro Branche korrekt

---

## 2. Finanzielle Berechnungen

### NPV-Berechnung: ✅ VALIDE

```python
NPV = -Investment + Σ(Jahr 1-20) [Jahres-Ersparnis × Degradation × (1 + Diskontrate)^-n]
```

**Parameter:**
- Diskontrate: 3% ✅ (marktüblich für langfristige Projekte)
- Projektlaufzeit: 20 Jahre ✅ (konservativ, PV hält 25+ Jahre)
- Degradation: 0.5%/Jahr ✅

### IRR-Berechnung: ✅ KORRIGIERT

**Vorher (FEHLERHAFT):**
```python
irr = (annual_savings / total_investment) * 100  # Einfache Rendite, KEINE IRR!
```

**Nachher (KORREKT):**
```python
# Newton-Raphson Iteration zur Bestimmung des Zinssatzes bei NPV = 0
def calculate_irr(investment, annual_cf, years, degradation):
    # Iterative Berechnung mit Konvergenzprüfung
    ...
```

### Amortisationsberechnung: ✅ VALIDE

```python
payback_years = total_investment / annual_savings
```

**Hinweis:** Dies ist die einfache Amortisation ohne Diskontierung. Für eine diskontierte Amortisation sollte zusätzlich der Break-Even-Punkt aus der NPV-Kurve berechnet werden (im Frontend bereits implementiert).

---

## 3. Investitionskosten

### Status: ✅ AKTUELL

**Aktuelle Marktpreise (Stand Dezember 2025):**

| Komponente | Code-Wert | Marktpreis 2025 | Status |
|------------|-----------|-----------------|--------|
| PV ≤30 kWp | 1.200 €/kWp | 1.000-1.200 €/kWp | ✅ |
| PV 30-100 kWp | 1.050 €/kWp | 950-1.100 €/kWp | ✅ |
| PV 100-500 kWp | 950 €/kWp | 900-1.000 €/kWp | ✅ |
| Speicher ≤30 kWh | 700 €/kWh | 600-750 €/kWh | ✅ |
| Speicher 30-100 kWh | 600 €/kWh | 550-650 €/kWh | ✅ |
| Speicher 100-500 kWh | 520 €/kWh | 480-550 €/kWh | ✅ |

**Quelle:** [photovoltaik.org/kosten](https://photovoltaik.org/kosten/photovoltaik-preise)

---

## 4. EEG-Einspeisevergütung

### Status: ✅ AKTUELL (Stand August 2025)

**Teileinspeisung (Überschusseinspeisung):**
| Anlagengröße | Code-Wert | Offizieller Wert |
|--------------|-----------|------------------|
| ≤ 10 kWp | 7,86 ct/kWh | 7,86 ct/kWh ✅ |
| 10-40 kWp | 6,80 ct/kWh | 6,80 ct/kWh ✅ |
| 40-100 kWp | 6,80 ct/kWh | 6,80 ct/kWh ✅ |

**Volleinspeisung:**
| Anlagengröße | Code-Wert | Offizieller Wert |
|--------------|-----------|------------------|
| ≤ 10 kWp | 12,47 ct/kWh | 12,47 ct/kWh ✅ |
| 10-40 kWp | 10,45 ct/kWh | 10,45 ct/kWh ✅ |

**Degression:** 1% alle 6 Monate ✅

**Quellen:**
- [Bundesnetzagentur EEG-Förderung](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/ErneuerbareEnergien/EEG_Foerderung/start.html)
- [enpal.de Einspeisevergütung 2025](https://www.enpal.de/photovoltaik/einspeiseverguetung)

---

## 5. Batterie-Parameter

### Status: ✅ VALIDE

| Parameter | Code-Wert | Fachliteratur | Status |
|-----------|-----------|---------------|--------|
| Lade-Effizienz | 95% | 94-96% | ✅ |
| Entlade-Effizienz | 95% | 94-96% | ✅ |
| Round-Trip-Effizienz | 90.25% | 88-92% (LFP) | ✅ |
| SOC Minimum | 10% | 10-20% | ✅ |
| SOC Maximum | 90% | 80-95% | ✅ |
| Zyklenlebensdauer | 6.000 | 5.000-8.000 (LFP) | ✅ |
| Kalendarische Lebensdauer | 15 Jahre | 15-20 Jahre | ✅ |

---

## 6. CO2-Emissionsfaktor

### Status: ✅ KORRIGIERT

**Vorher:** 0.380 kg CO2/kWh (Wert von 2023)

**Nachher:** 0.363 kg CO2/kWh

**Quelle:** [Umweltbundesamt - CO2-Emissionen 2024](https://www.umweltbundesamt.de/themen/co2-emissionen-pro-kilowattstunde-strom-2024)

**Historische Entwicklung:**
| Jahr | CO2-Faktor |
|------|------------|
| 2022 | 433 g/kWh |
| 2023 | 386 g/kWh |
| 2024 | 363 g/kWh |

---

## 7. Peak-Shaving-Berechnungen

### Status: ✅ VALIDE

**Leistungspreise (§14a EnWG):**
| Kategorie | Code-Wert | Marktdaten | Status |
|-----------|-----------|------------|--------|
| Niedrig (ländlich) | 60 €/kW/Jahr | 50-80 €/kW | ✅ |
| Mittel | 100 €/kW/Jahr | 80-120 €/kW | ✅ |
| Hoch (städtisch) | 150 €/kW/Jahr | 130-170 €/kW | ✅ |
| Sehr hoch | 250 €/kW/Jahr | 200-300 €/kW | ✅ |
| Extrem (Ballungsräume) | 440 €/kW/Jahr | 350-500 €/kW | ✅ |

**Berechnungslogik:**
- Perzentil-Analyse (90%) für Peak-Identifikation ✅
- Sicherheitsfaktor 1.15 für Batterie-Sizing ✅
- Mindestabstand 4h zwischen identifizierten Peaks ✅

---

## 8. Angebotsgenerierung

### Status: ⚠️ VERBESSERUNGSBEDARF

**Vorhandene Elemente:**
- ✅ Executive Summary
- ✅ Systemkonfiguration (PV kWp, Speicher kWh)
- ✅ Simulationsergebnisse (Autarkie, Einsparung)
- ✅ Wirtschaftlichkeitsanalyse
- ✅ CO2-Einsparung
- ✅ PDF-Generierung

**Fehlende Elemente für professionelle Angebote:**

| Element | Status | Priorität |
|---------|--------|-----------|
| Detaillierte Preisaufschlüsselung | ❌ Fehlt | HOCH |
| Spezifische Komponentenliste (BOM) | ⚠️ Optional | HOCH |
| Technische Datenblätter | ❌ Fehlt | MITTEL |
| Garantieinformationen | ❌ Fehlt | HOCH |
| Förderinformationen (KfW, Länder) | ❌ Fehlt | HOCH |
| Wartungs-/Service-Pakete | ❌ Fehlt | MITTEL |
| Zahlungsbedingungen | ❌ Fehlt | HOCH |
| AGB-Verweis | ❌ Fehlt | HOCH |
| Gültigkeitsdauer | ✅ Vorhanden | - |
| Unterschriftsfeld | ❌ Fehlt | MITTEL |

### Empfohlene Angebotsstruktur:

```
1. Deckblatt mit Angebotsnummer, Gültigkeit
2. Executive Summary (1 Seite)
3. Technische Konfiguration (1-2 Seiten)
   - Komponentenliste mit Modellen
   - Technische Datenblätter
4. Wirtschaftlichkeitsanalyse (1-2 Seiten)
   - Investitionsübersicht
   - Amortisationsrechnung
   - 20-Jahres-Prognose
5. Förderinformationen (1 Seite)
   - KfW-Kredite
   - Länderprogramme
   - MwSt-Befreiung
6. Preisaufschlüsselung (1 Seite)
   - Komponenten
   - Installation
   - Inbetriebnahme
   - Netzkosten
7. Service & Garantie (1 Seite)
8. Nächste Schritte & Unterschriften (1 Seite)
```

---

## 9. Zusammenfassung der Korrekturen

### Durchgeführte Änderungen:

1. **pvlib_simulator.py:517-550**
   - IRR-Berechnung durch Newton-Raphson-Methode ersetzt
   - Konvergenzprüfung implementiert

2. **config.py:306**
   - CO2-Faktor von 0.380 auf 0.363 aktualisiert

3. **claude_service.py** (mehrere Stellen)
   - CO2-Faktor von 0.4 auf 0.363 aktualisiert

---

## 10. Empfehlungen für zukünftige Wartung

1. **Halbjährliche Prüfung:**
   - EEG-Vergütungssätze (Degression alle 6 Monate)
   - Investitionskosten (Marktentwicklung)

2. **Jährliche Prüfung:**
   - CO2-Emissionsfaktor (UBA-Veröffentlichung)
   - Leistungspreise nach Regionen
   - §14a EnWG Regelungen

3. **Automatisierung:**
   - API-Integration für aktuelle EEG-Sätze
   - Dynamischer CO2-Faktor aus UBA-Daten

---

## Quellen

- [Umweltbundesamt - CO2-Emissionen](https://www.umweltbundesamt.de/themen/co2-emissionen-pro-kilowattstunde-strom-2024)
- [Bundesnetzagentur - EEG-Förderung](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/ErneuerbareEnergien/EEG_Foerderung/start.html)
- [photovoltaik.org - Kosten 2025](https://photovoltaik.org/kosten/photovoltaik-preise)
- [enpal.de - Einspeisevergütung](https://www.enpal.de/photovoltaik/einspeiseverguetung)
