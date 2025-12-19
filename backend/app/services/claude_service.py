"""
Claude AI Service
Intelligente Angebotserstellung mit Claude Opus 4.5

Phase 2 Features:
- KI-Optimierung mit intelligenter System-Dimensionierung
- Lastprofil-basierte Empfehlungen
- Automatische Angebotstexte
- Vergleichsszenarien
"""

from anthropic import Anthropic
from typing import Dict, List, Optional
import json
import logging
import re

from app.config import settings

logger = logging.getLogger(__name__)


# Load profile characteristics for dimensioning
LOAD_PROFILE_CHARACTERISTICS = {
    "office": {
        "name": "Büro",
        "peak_hours": "8-18 Uhr",
        "peak_days": "Mo-Fr",
        "baseload_factor": 0.15,
        "peak_factor": 1.0,
        "weekend_factor": 0.2,
        "pv_match_quality": "sehr gut",  # Good solar/demand overlap
        "recommended_battery_hours": 2,  # Hours of peak load
        "description": "Typisches Verbrauchsprofil mit hohem Eigenverbrauchspotenzial durch gute Übereinstimmung von PV-Erzeugung und Lastgang"
    },
    "retail": {
        "name": "Einzelhandel",
        "peak_hours": "10-20 Uhr",
        "peak_days": "Mo-Sa",
        "baseload_factor": 0.1,
        "peak_factor": 1.0,
        "weekend_factor": 0.7,
        "pv_match_quality": "gut",
        "recommended_battery_hours": 3,
        "description": "Längere Öffnungszeiten erfordern größeren Speicher für Abendstunden"
    },
    "production": {
        "name": "Produktion",
        "peak_hours": "6-22 Uhr",
        "peak_days": "Mo-Fr (teilweise Sa)",
        "baseload_factor": 0.3,
        "peak_factor": 1.0,
        "weekend_factor": 0.4,
        "pv_match_quality": "gut",
        "recommended_battery_hours": 4,
        "description": "Hoher Grundlastanteil ermöglicht konstante PV-Nutzung, Schichtbetrieb benötigt größeren Speicher"
    },
    "warehouse": {
        "name": "Lager/Logistik",
        "peak_hours": "6-18 Uhr",
        "peak_days": "Mo-Fr",
        "baseload_factor": 0.2,
        "peak_factor": 1.0,
        "weekend_factor": 0.3,
        "pv_match_quality": "sehr gut",
        "recommended_battery_hours": 2,
        "description": "Sehr gute PV-Eignung durch große Dachflächen und tageszeitliche Lastverteilung"
    }
}


class ClaudeService:
    """
    Service für KI-gestützte Funktionen mit Claude Opus 4.5
    
    Features:
    - Intelligente Angebots-Texte
    - System-Optimierung
    - Komponenten-Empfehlungen
    - Kundenspezifische Beratung
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        if self.api_key:
            self.client = Anthropic(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("ANTHROPIC_API_KEY nicht gesetzt - Claude-Features deaktiviert")
    
    async def generate_offer_text(
        self,
        project: Dict,
        simulation: Dict,
        components: Optional[List[Dict]] = None
    ) -> str:
        """
        Generiert professionellen, Enterprise-Grade Angebots-Text

        Args:
            project: Projektdaten (Kunde, Standort, System)
            simulation: Simulationsergebnisse (KPIs)
            components: Optionale Komponentenliste

        Returns:
            Formatierter Angebots-Text auf Deutsch mit Markdown-Struktur
        """
        if not self.client:
            return self._fallback_offer_text(project, simulation)

        # Erweiterte KPIs berechnen
        pv_generation = simulation.get('pv_generation_kwh', 0)
        co2_savings_tons = pv_generation * 0.363 / 1000  # kg CO2/kWh (UBA 2024)
        annual_savings = simulation.get('annual_savings_eur', 0)
        total_investment = simulation.get('total_investment_eur', 0)
        if total_investment == 0:
            total_investment = (
                project.get('pv_peak_power_kw', 0) * 1100 +
                project.get('battery_capacity_kwh', 0) * 600 + 2000
            )

        # Lastprofil-Info
        profile_type = project.get('load_profile_type', 'office')
        profile_info = LOAD_PROFILE_CHARACTERISTICS.get(profile_type, LOAD_PROFILE_CHARACTERISTICS['office'])

        # Enterprise-Grade System-Prompt
        system_prompt = """Du bist Senior Energy Consultant bei einem führenden deutschen
Energieunternehmen. Du erstellst professionelle Angebotstexte für Gewerbekunden, die:

1. Höchste Seriosität und Fachkompetenz ausstrahlen
2. Wirtschaftliche Kennzahlen präzise und verständlich präsentieren
3. Technische Exzellenz demonstrieren
4. Vertrauen durch Transparenz aufbauen
5. Entscheidungsträger auf C-Level überzeugen

STILRICHTLINIEN:
- Formelle Sie-Anrede durchgehend
- Keine Marketing-Floskeln oder übertriebene Versprechen
- Konkrete Zahlen und Fakten statt vager Aussagen
- Strukturierter Aufbau mit klaren Abschnitten
- Professionelle, aber zugängliche Sprache
- Markdown-Formatierung für Struktur"""

        user_prompt = f"""Erstelle einen professionellen Angebotstext für folgendes Gewerbeprojekt:

KUNDE:
- Ansprechpartner: {project.get('customer_name', 'Geschäftsführung')}
- Unternehmen: {project.get('customer_company') or project.get('customer_name', '')}
- Branche: {profile_info.get('name', 'Gewerbe')}
- Standort: {project.get('address', '')}, {project.get('postal_code', '')} {project.get('city', '')}

SYSTEMKONFIGURATION:
- PV-Anlage: {project.get('pv_peak_power_kw', 0):.1f} kWp
- Batteriespeicher: {project.get('battery_capacity_kwh', 0):.0f} kWh / {project.get('battery_power_kw', project.get('battery_capacity_kwh', 0) * 0.5):.0f} kW
- Jahresverbrauch: {project.get('annual_consumption_kwh', 0):,.0f} kWh
- Strompreis: {project.get('electricity_price_eur_kwh', 0.30):.2f} EUR/kWh

SIMULATIONSERGEBNISSE:
- PV-Erzeugung: {pv_generation:,.0f} kWh/Jahr
- Spezifischer Ertrag: {pv_generation / max(project.get('pv_peak_power_kw', 1), 1):,.0f} kWh/kWp
- Eigenverbrauch: {simulation.get('self_consumption_kwh', 0):,.0f} kWh ({simulation.get('self_consumption_ratio_percent', 0):.0f}%)
- Netzeinspeisung: {simulation.get('grid_export_kwh', 0):,.0f} kWh
- Restnetzbezug: {simulation.get('grid_import_kwh', 0):,.0f} kWh
- AUTARKIEGRAD: {simulation.get('autonomy_degree_percent', 0):.0f}%
- Speicher-Zyklen: {simulation.get('battery_cycles', 250):.0f}/Jahr

WIRTSCHAFTLICHKEIT:
- Investition (geschätzt): {total_investment:,.0f} EUR
- Jährliche Ersparnis: {annual_savings:,.0f} EUR
- Amortisation: {simulation.get('payback_period_years', 8):.1f} Jahre
- Ersparnis 20 Jahre: ca. {annual_savings * 18:,.0f} EUR
- CO2-Vermeidung: {co2_savings_tons:.1f} t/Jahr ({co2_savings_tons * 25:.0f} t über 25 Jahre)

AUFGABE:
Verfasse einen strukturierten, professionellen Angebotstext (ca. 450 Wörter) mit:

## Executive Summary
(3-4 Sätze: System-Highlights, Autarkiegrad, wichtigste Ersparnis-Kennzahl)

## Ihre maßgeschneiderte Systemlösung
(PV + Speicher Beschreibung, intelligentes Energiemanagement, Qualität)

## Wirtschaftlichkeitsanalyse
(Jährliche Ersparnis, Amortisation, langfristiger Wert mit konkreten Zahlen)

## Ihr Beitrag zur Nachhaltigkeit
(CO2-Einsparung konkret, unternehmerische Verantwortung)

## Nächste Schritte
(Konkreter Call-to-Action, Vor-Ort-Termin anbieten)

Verwende **fett** für wichtige Kennzahlen. Schreibe sachlich und professionell."""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2500,
                messages=[{"role": "user", "content": user_prompt}],
                system=system_prompt
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Claude API Fehler: {e}")
            return self._fallback_offer_text(project, simulation)
    
    async def optimize_system(
        self,
        project: Dict,
        optimization_target: str = "max-roi"
    ) -> Dict:
        """
        KI-basierte Systemoptimierung
        
        Args:
            project: Aktuelle Projektkonfiguration
            optimization_target: Optimierungsziel
                - "max-roi": Maximale Rendite
                - "max-autonomy": Maximale Unabhängigkeit
                - "min-cost": Minimale Kosten
                
        Returns:
            Optimierungsempfehlungen mit Begründung
        """
        if not self.client:
            return self._fallback_optimization(project, optimization_target)
        
        target_descriptions = {
            "max-roi": "Maximale Rendite (ROI) - schnellste Amortisation",
            "max-autonomy": "Maximale Unabhängigkeit vom Stromnetz",
            "min-cost": "Minimale Investitionskosten bei gutem ROI"
        }
        
        system_prompt = """Du bist ein Experte für die Dimensionierung von 
gewerblichen PV-Speichersystemen. Analysiere die Konfiguration und gib 
konkrete Optimierungsempfehlungen basierend auf deutschen Marktbedingungen 2025.

Berücksichtige:
- Typische Gewerbeverbrauchsprofile (Mo-Fr 8-18 Uhr)
- Aktuelle Komponentenpreise (PV: ~800-1200€/kWp, Speicher: ~400-600€/kWh)
- Einspeisevergütung ~8ct/kWh
- Strompreise 25-35ct/kWh
- Speicher-Degradation ~2%/Jahr

Antworte IMMER im JSON-Format."""

        user_prompt = f"""Optimiere dieses Gewerbeprojekt für: {target_descriptions.get(optimization_target, optimization_target)}

AKTUELLE KONFIGURATION:
- PV-Leistung: {project.get('pv_peak_power_kw', 0)} kWp
- Speicher: {project.get('battery_capacity_kwh', 0)} kWh
- Jahresverbrauch: {project.get('annual_consumption_kwh', 0):,.0f} kWh
- Strompreis: {project.get('electricity_price_eur_kwh', 0.30):.2f} €/kWh

Antworte NUR mit diesem JSON-Format:
{{
    "optimized_pv_kw": <number>,
    "optimized_battery_kwh": <number>,
    "optimized_battery_power_kw": <number>,
    "expected_autonomy_percent": <number>,
    "expected_savings_eur": <number>,
    "expected_payback_years": <number>,
    "investment_delta_eur": <number>,
    "recommendations": [
        "<konkrete Empfehlung 1>",
        "<konkrete Empfehlung 2>",
        "<konkrete Empfehlung 3>"
    ],
    "reasoning": "<Begründung in 2-3 Sätzen>"
}}"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                system=system_prompt
            )
            
            response_text = message.content[0].text
            
            # JSON aus Antwort extrahieren
            try:
                # Versuche direkt zu parsen
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Versuche JSON aus Text zu extrahieren
                import re
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    return self._fallback_optimization(project, optimization_target)
            
            return result
            
        except Exception as e:
            logger.error(f"Claude Optimization Fehler: {e}")
            return self._fallback_optimization(project, optimization_target)
    
    async def get_component_recommendations(
        self,
        project: Dict,
        budget_eur: Optional[float] = None
    ) -> List[Dict]:
        """
        KI-basierte Komponentenempfehlungen
        
        Args:
            project: Projektkonfiguration
            budget_eur: Optionales Budget-Limit
            
        Returns:
            Liste mit empfohlenen Komponenten
        """
        if not self.client:
            return self._fallback_components(project)
        
        system_prompt = """Du bist ein Experte für PV-Speicher-Komponenten im deutschen Markt.
Empfehle passende Komponenten basierend auf der Systemgröße und gängigen Marken.

Bekannte Hersteller:
- Wechselrichter: Fronius, SMA, Huawei, SolarEdge, Kostal
- Speicher: BYD, Huawei LUNA, SolarEdge, E3/DC, Sonnen
- Module: Trina, JA Solar, Longi, Canadian Solar, Jinko

Antworte im JSON-Format."""

        user_prompt = f"""Empfehle Komponenten für:
- PV-Leistung: {project.get('pv_peak_power_kw', 0)} kWp
- Speicher: {project.get('battery_capacity_kwh', 0)} kWh
{f'- Budget: {budget_eur:,.0f} €' if budget_eur else ''}

Antworte NUR mit diesem JSON-Array:
[
    {{
        "category": "inverter|battery|pv_module",
        "manufacturer": "<Hersteller>",
        "model": "<Modell>",
        "quantity": <Anzahl>,
        "unit_price_eur": <Preis>,
        "reason": "<Kurze Begründung>"
    }}
]"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                system=system_prompt
            )
            
            response_text = message.content[0].text
            
            try:
                result = json.loads(response_text)
                return result if isinstance(result, list) else []
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\[[\s\S]*\]', response_text)
                if json_match:
                    return json.loads(json_match.group())
                return self._fallback_components(project)
                
        except Exception as e:
            logger.error(f"Claude Components Fehler: {e}")
            return self._fallback_components(project)
    
    async def generate_customer_faq(
        self,
        project: Dict,
        simulation: Dict
    ) -> List[Dict]:
        """
        Generiert kundenspezifische FAQ für das Angebot
        """
        if not self.client:
            return self._fallback_faq()

        user_prompt = f"""Erstelle 5 kundenspezifische FAQ für ein PV-Speicher-Angebot:

System: {project.get('pv_peak_power_kw', 0)} kWp PV + {project.get('battery_capacity_kwh', 0)} kWh Speicher
Autarkie: {simulation.get('autonomy_degree_percent', 0):.0f}%
Einsparung: {simulation.get('annual_savings_eur', 0):,.0f} €/Jahr

Antworte NUR als JSON-Array:
[
    {{"question": "...", "answer": "..."}},
    ...
]"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                messages=[{"role": "user", "content": user_prompt}]
            )

            response_text = message.content[0].text

            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                json_match = re.search(r'\[[\s\S]*\]', response_text)
                if json_match:
                    return json.loads(json_match.group())
                return self._fallback_faq()

        except Exception as e:
            logger.error(f"Claude FAQ Fehler: {e}")
            return self._fallback_faq()

    async def dimension_system(
        self,
        project: Dict,
        constraints: Optional[Dict] = None
    ) -> Dict:
        """
        KI-basierte System-Dimensionierung basierend auf Lastprofil

        Berechnet optimale PV- und Speichergröße basierend auf:
        - Lastprofil-Typ (Büro, Einzelhandel, Produktion, Lager)
        - Jahresverbrauch
        - Dachfläche (falls vorhanden)
        - Budget-Constraints (optional)
        - Strompreis und Einspeisevergütung

        Args:
            project: Projektdaten inkl. load_profile_type
            constraints: Optionale Einschränkungen (max_budget, max_roof_area, etc.)

        Returns:
            Dict mit optimaler Dimensionierung und Begründung
        """
        load_profile_type = project.get('load_profile_type', 'office')
        profile_info = LOAD_PROFILE_CHARACTERISTICS.get(load_profile_type, LOAD_PROFILE_CHARACTERISTICS['office'])

        if not self.client:
            return self._fallback_dimensioning(project, profile_info, constraints)

        system_prompt = """Du bist ein Experte für die Dimensionierung von gewerblichen
PV-Speichersystemen in Deutschland. Du analysierst Lastprofile und berechnest
die optimale System-Dimensionierung basierend auf aktuellen Marktbedingungen 2025.

Wichtige Dimensionierungsregeln:
1. PV-Leistung: ~950-1100 kWh Ertrag pro kWp in Deutschland
2. Eigenverbrauchsoptimierung: PV sollte nicht mehr als 150% des Tagesbedarfs erzeugen
3. Speicher: Typisch 1-3 Stunden des Peak-Bedarfs für Gewerbe
4. ROI-Optimum: Speicher-zu-PV-Verhältnis von 1:1 bis 2:1 (kWh:kWp)
5. Lastprofil-Anpassung: Büro = kleine Speicher, Produktion = größere Speicher

Antworte IMMER im JSON-Format."""

        constraints_text = ""
        if constraints:
            if constraints.get('max_budget'):
                constraints_text += f"\n- Maximales Budget: {constraints['max_budget']:,.0f} €"
            if constraints.get('max_roof_area'):
                constraints_text += f"\n- Maximale Dachfläche: {constraints['max_roof_area']} m²"
            if constraints.get('min_autonomy'):
                constraints_text += f"\n- Mindest-Autarkiegrad: {constraints['min_autonomy']}%"

        user_prompt = f"""Dimensioniere ein PV-Speichersystem für folgendes Gewerbeprojekt:

## PROJEKTDATEN
- Jahresverbrauch: {project.get('annual_consumption_kwh', 50000):,.0f} kWh
- Spitzenlast: {project.get('peak_load_kw', project.get('annual_consumption_kwh', 50000) / 2000):.0f} kW
- Lastprofil: {profile_info['name']} ({load_profile_type})
- Lastspitzen: {profile_info['peak_hours']} an {profile_info['peak_days']}
- PV-Eignung: {profile_info['pv_match_quality']}
- Strompreis: {project.get('electricity_price_eur_kwh', 0.30):.2f} €/kWh
- Einspeisevergütung: {project.get('feed_in_tariff_eur_kwh', 0.08):.2f} €/kWh
- Standort: {project.get('city', 'Deutschland')} (Lat: {project.get('latitude', 51.0):.2f})
{f"- Dachfläche: {project.get('roof_area_sqm', 'unbekannt')} m²" if project.get('roof_area_sqm') else ""}
{constraints_text if constraints_text else ""}

## LASTPROFIL-CHARAKTERISTIK
{profile_info['description']}

## AUFGABE
Berechne die optimale Dimensionierung für maximalen ROI mit mindestens 50% Autarkiegrad.

Antworte NUR mit diesem JSON-Format:
{{
    "recommended_pv_kw": <float>,
    "recommended_battery_kwh": <float>,
    "recommended_battery_power_kw": <float>,
    "expected_results": {{
        "autonomy_percent": <float>,
        "self_consumption_percent": <float>,
        "annual_savings_eur": <float>,
        "payback_years": <float>,
        "co2_savings_tons": <float>
    }},
    "investment": {{
        "pv_cost_eur": <float>,
        "battery_cost_eur": <float>,
        "installation_cost_eur": <float>,
        "total_cost_eur": <float>
    }},
    "dimensioning_factors": {{
        "pv_to_consumption_ratio": <float>,
        "battery_to_pv_ratio": <float>,
        "specific_yield_kwh_per_kwp": <int>
    }},
    "reasoning": "<2-3 Sätze Begründung>",
    "recommendations": [
        "<Empfehlung 1>",
        "<Empfehlung 2>",
        "<Empfehlung 3>"
    ]
}}"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                messages=[{"role": "user", "content": user_prompt}],
                system=system_prompt
            )

            response_text = message.content[0].text

            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    return self._fallback_dimensioning(project, profile_info, constraints)

            return result

        except Exception as e:
            logger.error(f"Claude Dimensioning Fehler: {e}")
            return self._fallback_dimensioning(project, profile_info, constraints)

    async def generate_comparison_scenarios(
        self,
        project: Dict,
        simulation: Dict
    ) -> Dict:
        """
        Generiert Vergleichsszenarien für verschiedene Systemkonfigurationen

        Erstellt 3 Szenarien:
        1. Basis (aktuelle Konfiguration)
        2. Wirtschaftlich optimal (max ROI)
        3. Autarkie optimal (max Unabhängigkeit)

        Args:
            project: Aktuelle Projektkonfiguration
            simulation: Aktuelle Simulationsergebnisse

        Returns:
            Dict mit 3 Vergleichsszenarien
        """
        if not self.client:
            return self._fallback_comparison(project, simulation)

        system_prompt = """Du bist ein Experte für PV-Speicher-Systeme und erstellst
Vergleichsszenarien für Gewerbekunden. Erstelle realistische Szenarien basierend
auf aktuellen deutschen Marktbedingungen 2025.

Preise:
- PV: ~1100 €/kWp (inkl. Installation)
- Speicher: ~600 €/kWh (LFP)
- Fixkosten: ~2000 €

Ertrag:
- Deutschland Nord: ~900-950 kWh/kWp
- Deutschland Mitte: ~950-1000 kWh/kWp
- Deutschland Süd: ~1000-1100 kWh/kWp

Antworte im JSON-Format."""

        user_prompt = f"""Erstelle 3 Vergleichsszenarien für folgendes Projekt:

## AKTUELLE KONFIGURATION (BASIS)
- PV: {project.get('pv_peak_power_kw', 50)} kWp
- Speicher: {project.get('battery_capacity_kwh', 100)} kWh
- Verbrauch: {project.get('annual_consumption_kwh', 50000):,.0f} kWh/Jahr
- Strompreis: {project.get('electricity_price_eur_kwh', 0.30):.2f} €/kWh

## AKTUELLE ERGEBNISSE
- Autarkie: {simulation.get('autonomy_degree_percent', 0):.0f}%
- Einsparung: {simulation.get('annual_savings_eur', 0):,.0f} €/Jahr
- Amortisation: {simulation.get('payback_period_years', 0):.1f} Jahre

## AUFGABE
Erstelle 3 Szenarien:
1. **Basis**: Aktuelle Konfiguration mit echten Werten
2. **ROI-Optimiert**: Schnellste Amortisation, moderate Autarkie
3. **Autarkie-Optimiert**: Maximale Unabhängigkeit, längere Amortisation

Antworte NUR mit diesem JSON:
{{
    "scenarios": [
        {{
            "name": "Basis",
            "description": "Aktuelle Konfiguration",
            "pv_kw": <float>,
            "battery_kwh": <float>,
            "investment_eur": <float>,
            "autonomy_percent": <float>,
            "annual_savings_eur": <float>,
            "payback_years": <float>,
            "npv_20y_eur": <float>,
            "co2_savings_tons": <float>,
            "highlight": "<Hauptvorteil>"
        }},
        {{
            "name": "ROI-Optimiert",
            ...
        }},
        {{
            "name": "Autarkie-Optimiert",
            ...
        }}
    ],
    "recommendation": "<Welches Szenario wird empfohlen und warum>",
    "comparison_summary": "<Kurzer Vergleich der 3 Optionen>"
}}"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": user_prompt}],
                system=system_prompt
            )

            response_text = message.content[0].text

            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    return self._fallback_comparison(project, simulation)

            return result

        except Exception as e:
            logger.error(f"Claude Comparison Fehler: {e}")
            return self._fallback_comparison(project, simulation)

    async def generate_detailed_offer_text(
        self,
        project: Dict,
        simulation: Dict,
        components: Optional[List[Dict]] = None,
        include_monthly: bool = True
    ) -> Dict:
        """
        Generiert detaillierten Angebotstext mit allen Abschnitten

        Returns:
            Dict mit separaten Textabschnitten für modulare Verwendung
        """
        if not self.client:
            return self._fallback_detailed_offer(project, simulation)

        monthly_text = ""
        if include_monthly and simulation.get('monthly_summary'):
            monthly_data = simulation['monthly_summary']
            summer_gen = sum(m['pv_generation_kwh'] for m in monthly_data[4:9])  # Mai-Sep
            winter_gen = sum(m['pv_generation_kwh'] for m in monthly_data[:3] + monthly_data[10:])  # Nov-Mrz
            monthly_text = f"""
## MONATLICHE VERTEILUNG
- Sommer (Mai-Sep): {summer_gen:,.0f} kWh ({summer_gen/simulation.get('pv_generation_kwh', 1)*100:.0f}% der Jahreserzeugung)
- Winter (Nov-Mrz): {winter_gen:,.0f} kWh
- Speicher gleicht saisonale Schwankungen teilweise aus
"""

        system_prompt = """Du erstellst professionelle, überzeugende Angebotstexte für
gewerbliche PV-Speicherlösungen. Der Text soll modular in verschiedene Abschnitte
unterteilt sein für flexible Verwendung in Dokumenten.

Stil: Professionell, sachlich, überzeugend ohne übertrieben werblich zu sein.
Sprache: Deutsch, Sie-Form
Fokus: Wirtschaftliche Vorteile und Fakten aus der Simulation"""

        user_prompt = f"""Erstelle einen detaillierten Angebotstext für:

## KUNDE
- Name: {project.get('customer_name', 'Kunde')}
- Unternehmen: {project.get('customer_company', '')}
- Standort: {project.get('address', '')}, {project.get('postal_code', '')} {project.get('city', '')}

## SYSTEM
- PV: {project.get('pv_peak_power_kw', 0)} kWp
- Speicher: {project.get('battery_capacity_kwh', 0)} kWh / {project.get('battery_power_kw', 0)} kW
- Jahresverbrauch: {project.get('annual_consumption_kwh', 0):,.0f} kWh

## SIMULATION
- PV-Erzeugung: {simulation.get('pv_generation_kwh', 0):,.0f} kWh/Jahr
- Autarkie: {simulation.get('autonomy_degree_percent', 0):.0f}%
- Eigenverbrauch: {simulation.get('self_consumption_ratio_percent', 0):.0f}%
- Jährliche Einsparung: {simulation.get('annual_savings_eur', 0):,.0f} €
- Amortisation: {simulation.get('payback_period_years', 0):.1f} Jahre
- CO2-Einsparung: {simulation.get('pv_generation_kwh', 0) * 0.363 / 1000:.1f} t/Jahr
{monthly_text}

## AUFGABE
Erstelle modularen Angebotstext als JSON:
{{
    "greeting": "<Persönliche Anrede, 1-2 Sätze>",
    "executive_summary": "<Management Summary, 3-4 Sätze mit Key Facts>",
    "system_description": "<Technische Beschreibung, 4-5 Sätze>",
    "economic_benefits": "<Wirtschaftliche Vorteile, 4-5 Sätze mit Zahlen>",
    "environmental_benefits": "<Umweltvorteile, 2-3 Sätze>",
    "next_steps": "<Call-to-Action, 2-3 Sätze>",
    "closing": "<Abschluss mit Grußformel>"
}}"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": user_prompt}],
                system=system_prompt
            )

            response_text = message.content[0].text

            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    return self._fallback_detailed_offer(project, simulation)

            return result

        except Exception as e:
            logger.error(f"Claude Detailed Offer Fehler: {e}")
            return self._fallback_detailed_offer(project, simulation)
    
    # ============ FALLBACK METHODS ============
    
    def _fallback_offer_text(self, project: Dict, simulation: Dict) -> str:
        """Fallback wenn Claude nicht verfügbar - Enterprise-Grade Template"""
        customer = project.get('customer_name', 'Geschäftsführung')
        company = project.get('customer_company') or customer
        city = project.get('city', project.get('postal_code', ''))
        pv_kw = project.get('pv_peak_power_kw', 0)
        battery_kwh = project.get('battery_capacity_kwh', 0)
        consumption = project.get('annual_consumption_kwh', 0)

        pv_generation = simulation.get('pv_generation_kwh', 0)
        autonomy = simulation.get('autonomy_degree_percent', 0)
        savings = simulation.get('annual_savings_eur', 0)
        payback = simulation.get('payback_period_years', 8)
        co2_tons = pv_generation * 0.363 / 1000  # kg CO2/kWh (UBA 2024)

        total_investment = pv_kw * 1100 + battery_kwh * 600 + 2000

        return f"""## Executive Summary

Sehr geehrte Damen und Herren,

für Ihren Standort in {city} haben wir eine individuelle PV-Speicherlösung konzipiert. Mit einer **{pv_kw:.0f} kWp Photovoltaikanlage** und einem **{battery_kwh:.0f} kWh Batteriespeicher** erreichen Sie einen **Autarkiegrad von {autonomy:.0f}%**. Die prognostizierte jährliche Ersparnis beträgt **{savings:,.0f} EUR**.

## Ihre maßgeschneiderte Systemlösung

Das für {company} dimensionierte System umfasst eine leistungsstarke Photovoltaikanlage mit {pv_kw:.0f} kWp Nennleistung, die jährlich ca. {pv_generation:,.0f} kWh Solarstrom erzeugt. Der integrierte Lithium-Eisenphosphat-Speicher mit {battery_kwh:.0f} kWh Kapazität optimiert Ihren Eigenverbrauch, indem überschüssiger Solarstrom zwischengespeichert und bei Bedarf wieder abgegeben wird.

Ein intelligentes Energiemanagementsystem koordiniert automatisch PV-Erzeugung, Speicherladung und Verbrauch, um Ihren Eigenverbrauchsanteil zu maximieren und den Netzbezug zu minimieren.

## Wirtschaftlichkeitsanalyse

Basierend auf Ihrem Jahresverbrauch von {consumption:,.0f} kWh und dem aktuellen Strompreis erzielen Sie folgende wirtschaftliche Vorteile:

- **Jährliche Ersparnis:** {savings:,.0f} EUR
- **Amortisationszeit:** {payback:.1f} Jahre
- **Gesamtersparnis (20 Jahre):** ca. {savings * 18:,.0f} EUR (inkl. Degradation)
- **Geschätzte Investition:** ca. {total_investment:,.0f} EUR

Nach der Amortisation profitieren Sie für weitere 15+ Jahre von nahezu kostenlosem Solarstrom.

## Ihr Beitrag zur Nachhaltigkeit

Mit dieser Anlage vermeiden Sie jährlich ca. **{co2_tons:.1f} Tonnen CO₂-Emissionen**. Über die Lebensdauer von 25 Jahren entspricht dies ca. {co2_tons * 25:.0f} Tonnen eingespartem Kohlendioxid – ein bedeutender Beitrag zum Klimaschutz und zur Erreichung Ihrer Nachhaltigkeitsziele.

## Nächste Schritte

Gerne präsentieren wir Ihnen die detaillierte Planung in einem persönlichen Gespräch. Wir vereinbaren einen Vor-Ort-Termin, um die technischen Gegebenheiten zu prüfen und Ihnen ein verbindliches Angebot zu unterbreiten.

Kontaktieren Sie uns für Ihre individuelle Beratung.

Mit freundlichen Grüßen,
Ihr EWS Energieberatungs-Team
"""
    
    def _fallback_optimization(self, project: Dict, target: str) -> Dict:
        """Fallback-Optimierung basierend auf Faustregeln"""
        consumption = project.get('annual_consumption_kwh', 50000)
        current_pv = project.get('pv_peak_power_kw', 50)
        current_battery = project.get('battery_capacity_kwh', 100)
        
        # Faustregeln für Gewerbe
        if target == "max-autonomy":
            # Größeres System für max. Unabhängigkeit
            opt_pv = max(consumption / 900, current_pv * 1.3)  # ~900 kWh/kWp
            opt_battery = max(consumption / 365 * 0.5, current_battery * 1.5)  # 50% Tagesverbrauch
        elif target == "min-cost":
            # Kleineres, effizientes System
            opt_pv = consumption / 1100  # Konservativer
            opt_battery = opt_pv * 1.5  # Kleinerer Speicher
        else:  # max-roi
            # Optimales Verhältnis
            opt_pv = consumption / 1000
            opt_battery = opt_pv * 2
        
        return {
            "optimized_pv_kw": round(opt_pv, 1),
            "optimized_battery_kwh": round(opt_battery, 1),
            "optimized_battery_power_kw": round(opt_battery * 0.5, 1),
            "expected_autonomy_percent": 65 if target == "max-autonomy" else 50,
            "expected_savings_eur": round(consumption * 0.15),  # ~15ct/kWh Ersparnis
            "expected_payback_years": 8.5,
            "investment_delta_eur": round((opt_pv - current_pv) * 1000 + (opt_battery - current_battery) * 500),
            "recommendations": [
                "PV-Anlage auf Süddach optimieren",
                "Speicher für Peak-Shaving dimensionieren",
                "Lastmanagement für E-Fahrzeuge prüfen"
            ],
            "reasoning": "Basierend auf Ihrem Verbrauchsprofil und aktuellen Marktpreisen."
        }
    
    def _fallback_components(self, project: Dict) -> List[Dict]:
        """Fallback-Komponentenempfehlung"""
        pv_kw = project.get('pv_peak_power_kw', 50)
        battery_kwh = project.get('battery_capacity_kwh', 100)
        
        return [
            {
                "category": "inverter",
                "manufacturer": "Huawei",
                "model": f"SUN2000-{min(100, int(pv_kw))}KTL-M3",
                "quantity": 1,
                "unit_price_eur": pv_kw * 80,
                "reason": "Hoher Wirkungsgrad, gutes Preis-Leistungs-Verhältnis"
            },
            {
                "category": "battery",
                "manufacturer": "BYD",
                "model": "Battery-Box Premium HVS",
                "quantity": int(battery_kwh / 12.8) + 1,
                "unit_price_eur": 5500,
                "reason": "Modularer Aufbau, LFP-Technologie, 10 Jahre Garantie"
            },
            {
                "category": "pv_module",
                "manufacturer": "Trina Solar",
                "model": "Vertex S+ 445W",
                "quantity": int(pv_kw * 1000 / 445) + 1,
                "unit_price_eur": 165,
                "reason": "n-Type TOPCon, hohe Effizienz, bifazial"
            }
        ]
    
    def _fallback_faq(self) -> List[Dict]:
        """Fallback FAQ"""
        return [
            {
                "question": "Wie lange hält der Speicher?",
                "answer": "Moderne LFP-Speicher sind für 6.000+ Zyklen ausgelegt, was bei täglicher Nutzung ca. 15-20 Jahre entspricht. Die Garantie beträgt in der Regel 10 Jahre."
            },
            {
                "question": "Was passiert bei Stromausfall?",
                "answer": "Mit einer Notstrom-Funktion kann der Speicher bei Netzausfall Ihre wichtigsten Verbraucher weiter versorgen. Dies erfordert einen kompatiblen Hybrid-Wechselrichter."
            },
            {
                "question": "Wie wird der Strom verteilt?",
                "answer": "Das Energiemanagement priorisiert automatisch: 1. Eigenverbrauch, 2. Speicher laden, 3. Netzeinspeisung. So wird Ihre Eigenverbrauchsquote maximiert."
            },
            {
                "question": "Welche Wartung ist nötig?",
                "answer": "PV-Speichersysteme sind weitgehend wartungsfrei. Eine jährliche Sichtprüfung und alle 2-3 Jahre eine Überprüfung durch einen Fachbetrieb werden empfohlen."
            },
            {
                "question": "Kann das System erweitert werden?",
                "answer": "Ja, modulare Speichersysteme können bei Bedarf erweitert werden. Auch eine spätere Ergänzung um eine Wallbox für E-Fahrzeuge ist problemlos möglich."
            }
        ]

    def _fallback_dimensioning(
        self,
        project: Dict,
        profile_info: Dict,
        constraints: Optional[Dict] = None
    ) -> Dict:
        """Fallback System-Dimensionierung basierend auf Faustregeln"""
        consumption = project.get('annual_consumption_kwh', 50000)
        electricity_price = project.get('electricity_price_eur_kwh', 0.30)

        # Dimensionierung basierend auf Verbrauch und Lastprofil
        # PV: ca. 1 kWp pro 1000 kWh Jahresverbrauch
        recommended_pv = consumption / 1000

        # Speicher basierend auf Lastprofil
        battery_hours = profile_info.get('recommended_battery_hours', 2)
        peak_load = project.get('peak_load_kw', consumption / 2000)
        recommended_battery = peak_load * battery_hours

        # Budget-Einschränkungen anwenden
        if constraints:
            max_budget = constraints.get('max_budget')
            if max_budget:
                # Grobe Kostenrechnung
                pv_cost = recommended_pv * 1100
                battery_cost = recommended_battery * 600
                total = pv_cost + battery_cost + 2000
                if total > max_budget:
                    factor = (max_budget - 2000) / (pv_cost + battery_cost)
                    recommended_pv *= factor
                    recommended_battery *= factor

            max_roof = constraints.get('max_roof_area')
            if max_roof:
                # ca. 6 m² pro kWp
                max_pv = max_roof / 6
                recommended_pv = min(recommended_pv, max_pv)

        # Kosten berechnen
        pv_cost = recommended_pv * 1100
        battery_cost = recommended_battery * 600
        installation_cost = 2000
        total_cost = pv_cost + battery_cost + installation_cost

        # Erwartete Ergebnisse
        pv_generation = recommended_pv * 950  # kWh/Jahr
        self_consumption_ratio = min(90, 50 + recommended_battery / recommended_pv * 10) if recommended_pv > 0 else 0
        self_consumed = pv_generation * self_consumption_ratio / 100
        grid_export = pv_generation - self_consumed
        grid_import = max(0, consumption - self_consumed)

        annual_savings = (
            self_consumed * electricity_price +
            grid_export * 0.08 -
            consumption * 0.02  # Netzzugang
        )
        payback = total_cost / annual_savings if annual_savings > 0 else 99
        autonomy = ((consumption - grid_import) / consumption * 100) if consumption > 0 else 0
        co2_savings = pv_generation * 0.363 / 1000  # Tonnen (UBA 2024)

        return {
            "recommended_pv_kw": round(recommended_pv, 1),
            "recommended_battery_kwh": round(recommended_battery, 1),
            "recommended_battery_power_kw": round(recommended_battery * 0.5, 1),
            "expected_results": {
                "autonomy_percent": round(autonomy, 1),
                "self_consumption_percent": round(self_consumption_ratio, 1),
                "annual_savings_eur": round(annual_savings, 0),
                "payback_years": round(min(payback, 25), 1),
                "co2_savings_tons": round(co2_savings, 1)
            },
            "investment": {
                "pv_cost_eur": round(pv_cost, 0),
                "battery_cost_eur": round(battery_cost, 0),
                "installation_cost_eur": round(installation_cost, 0),
                "total_cost_eur": round(total_cost, 0)
            },
            "dimensioning_factors": {
                "pv_to_consumption_ratio": round(recommended_pv / (consumption / 1000), 2) if consumption > 0 else 0,
                "battery_to_pv_ratio": round(recommended_battery / recommended_pv, 2) if recommended_pv > 0 else 0,
                "specific_yield_kwh_per_kwp": 950
            },
            "reasoning": f"Dimensionierung optimiert für {profile_info['name']}-Lastprofil mit {profile_info['pv_match_quality']}er PV-Eignung. "
                        f"Speicher für {battery_hours}h Peak-Abdeckung ausgelegt.",
            "recommendations": [
                "PV-Ausrichtung Süd optimieren für maximalen Ertrag",
                f"Speicher kann Last während {profile_info['peak_hours']} abfedern",
                "Lastmanagement für weitere Optimierung prüfen"
            ]
        }

    def _fallback_comparison(self, project: Dict, simulation: Dict) -> Dict:
        """Fallback Vergleichsszenarien"""
        pv = project.get('pv_peak_power_kw', 50)
        battery = project.get('battery_capacity_kwh', 100)
        autonomy = simulation.get('autonomy_degree_percent', 50)
        savings = simulation.get('annual_savings_eur', 5000)
        payback = simulation.get('payback_period_years', 8)

        # Basis-Investment
        base_investment = pv * 1100 + battery * 600 + 2000

        # ROI-optimiert: kleinerer Speicher
        roi_pv = pv * 0.9
        roi_battery = battery * 0.6
        roi_investment = roi_pv * 1100 + roi_battery * 600 + 2000

        # Autarkie-optimiert: größeres System
        auto_pv = pv * 1.3
        auto_battery = battery * 1.5
        auto_investment = auto_pv * 1100 + auto_battery * 600 + 2000

        return {
            "scenarios": [
                {
                    "name": "Basis",
                    "description": "Aktuelle Konfiguration",
                    "pv_kw": pv,
                    "battery_kwh": battery,
                    "investment_eur": round(base_investment, 0),
                    "autonomy_percent": autonomy,
                    "annual_savings_eur": savings,
                    "payback_years": payback,
                    "npv_20y_eur": round(savings * 15 - base_investment, 0),
                    "co2_savings_tons": round(pv * 0.95 * 0.363, 1),
                    "highlight": "Ausgewogenes Verhältnis"
                },
                {
                    "name": "ROI-Optimiert",
                    "description": "Maximale Rendite",
                    "pv_kw": round(roi_pv, 1),
                    "battery_kwh": round(roi_battery, 1),
                    "investment_eur": round(roi_investment, 0),
                    "autonomy_percent": round(autonomy * 0.85, 1),
                    "annual_savings_eur": round(savings * 0.9, 0),
                    "payback_years": round(payback * 0.85, 1),
                    "npv_20y_eur": round(savings * 0.9 * 15 - roi_investment, 0),
                    "co2_savings_tons": round(roi_pv * 0.95 * 0.363, 1),
                    "highlight": "Schnellste Amortisation"
                },
                {
                    "name": "Autarkie-Optimiert",
                    "description": "Maximale Unabhängigkeit",
                    "pv_kw": round(auto_pv, 1),
                    "battery_kwh": round(auto_battery, 1),
                    "investment_eur": round(auto_investment, 0),
                    "autonomy_percent": min(85, round(autonomy * 1.25, 1)),
                    "annual_savings_eur": round(savings * 1.2, 0),
                    "payback_years": round(payback * 1.1, 1),
                    "npv_20y_eur": round(savings * 1.2 * 15 - auto_investment, 0),
                    "co2_savings_tons": round(auto_pv * 0.95 * 0.363, 1),
                    "highlight": "Maximale Unabhängigkeit"
                }
            ],
            "recommendation": "Für die meisten Gewerbekunden empfehlen wir das Basis-Szenario als optimalen Kompromiss zwischen Wirtschaftlichkeit und Unabhängigkeit.",
            "comparison_summary": "Das ROI-optimierte Szenario amortisiert sich am schnellsten, bietet aber weniger Unabhängigkeit. Das Autarkie-Szenario maximiert die Eigenversorgung bei höherer Investition."
        }

    def _fallback_detailed_offer(self, project: Dict, simulation: Dict) -> Dict:
        """Fallback detaillierter Angebotstext"""
        customer = project.get('customer_name', 'Kunde')
        city = project.get('city', '')
        pv = project.get('pv_peak_power_kw', 0)
        battery = project.get('battery_capacity_kwh', 0)
        consumption = project.get('annual_consumption_kwh', 0)

        autonomy = simulation.get('autonomy_degree_percent', 0)
        savings = simulation.get('annual_savings_eur', 0)
        payback = simulation.get('payback_period_years', 0)
        pv_gen = simulation.get('pv_generation_kwh', 0)
        co2 = pv_gen * 0.363 / 1000  # kg CO2/kWh (UBA 2024)

        return {
            "greeting": f"Sehr geehrte/r {customer}, vielen Dank für Ihr Interesse an einer nachhaltigen Energielösung für Ihren Standort{' in ' + city if city else ''}.",
            "executive_summary": f"Wir haben für Sie ein PV-Speichersystem mit {pv:.0f} kWp und {battery:.0f} kWh Speicher dimensioniert. "
                                f"Damit erreichen Sie einen Autarkiegrad von {autonomy:.0f}% und sparen jährlich {savings:,.0f} €. "
                                f"Die Investition amortisiert sich in {payback:.1f} Jahren.",
            "system_description": f"Das System besteht aus einer {pv:.0f} kWp Photovoltaikanlage kombiniert mit einem {battery:.0f} kWh Lithium-Eisenphosphat-Speicher. "
                                f"Die PV-Anlage erzeugt jährlich ca. {pv_gen:,.0f} kWh Solarstrom. "
                                "Der Speicher optimiert Ihren Eigenverbrauch, indem er überschüssigen Solarstrom zwischenspeichert. "
                                "Ein intelligentes Energiemanagement koordiniert PV-Erzeugung, Speicher und Verbrauch automatisch.",
            "economic_benefits": f"Bei Ihrem Jahresverbrauch von {consumption:,.0f} kWh und aktuellen Strompreisen erzielen Sie eine jährliche Ersparnis von {savings:,.0f} €. "
                                f"Über 20 Jahre summiert sich dies auf über {savings * 18:,.0f} € (inkl. Degradation). "
                                f"Die Amortisation erfolgt nach nur {payback:.1f} Jahren. "
                                "Danach profitieren Sie von nahezu kostenlosem Solarstrom für weitere 15+ Jahre.",
            "environmental_benefits": f"Mit dieser Anlage vermeiden Sie jährlich ca. {co2:.1f} Tonnen CO₂-Emissionen. "
                                    f"Über die Lebensdauer von 25 Jahren entspricht das ca. {co2 * 25:.0f} Tonnen eingespartem CO₂.",
            "next_steps": "Gerne erstellen wir Ihnen ein verbindliches Angebot mit detaillierter Komponentenliste. "
                        "Kontaktieren Sie uns für einen Vor-Ort-Termin zur finalen Planung.",
            "closing": "Mit sonnigen Grüßen,\nIhr EWS Team"
        }


# Singleton Instance
_claude_service: Optional[ClaudeService] = None

def get_claude_service() -> ClaudeService:
    """Get or create Claude service instance"""
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeService()
    return _claude_service
