"""
Claude AI Service
Intelligente Angebotserstellung mit Claude Opus 4.5
"""

from anthropic import Anthropic
from typing import Dict, List, Optional
import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)


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
        Generiert professionellen, überzeugenden Angebots-Text
        
        Args:
            project: Projektdaten (Kunde, Standort, System)
            simulation: Simulationsergebnisse (KPIs)
            components: Optionale Komponentenliste
            
        Returns:
            Formatierter Angebots-Text auf Deutsch
        """
        if not self.client:
            return self._fallback_offer_text(project, simulation)
        
        # System-Prompt für konsistente Ergebnisse
        system_prompt = """Du bist ein erfahrener Energieberater und Vertriebsexperte 
für gewerbliche PV-Speichersysteme in Deutschland. Du schreibst professionelle, 
überzeugende Angebots-Texte die:

1. Wirtschaftliche Vorteile klar herausstellen
2. Technische Details verständlich erklären
3. Umweltvorteile betonen
4. Vertrauen aufbauen
5. Zum Handeln motivieren

Schreibe auf Deutsch, professionell aber zugänglich. Vermeide übertriebene 
Verkaufssprache. Nutze konkrete Zahlen aus den Simulationsergebnissen."""

        # User-Prompt mit allen relevanten Daten
        user_prompt = f"""Erstelle einen Angebots-Text für folgendes PV-Speicherprojekt:

## KUNDENDATEN
- Kunde: {project.get('customer_name', 'Kunde')}
- Unternehmen: {project.get('customer_company', project.get('customer_name', ''))}
- Standort: {project.get('address', '')}, {project.get('postal_code', '')} {project.get('city', '')}

## SYSTEMKONFIGURATION
- PV-Leistung: {project.get('pv_peak_power_kw', 0)} kWp
- Speicherkapazität: {project.get('battery_capacity_kwh', 0)} kWh
- Speicherleistung: {project.get('battery_power_kw', 0)} kW
- Jahresverbrauch: {project.get('annual_consumption_kwh', 0):,.0f} kWh
- Aktueller Strompreis: {project.get('electricity_price_eur_kwh', 0.30):.2f} €/kWh

## SIMULATIONSERGEBNISSE
- PV-Erzeugung: {simulation.get('pv_generation_kwh', 0):,.0f} kWh/Jahr
- Eigenverbrauch: {simulation.get('self_consumption_kwh', 0):,.0f} kWh/Jahr
- Netzeinspeisung: {simulation.get('grid_export_kwh', 0):,.0f} kWh/Jahr
- Netzbezug: {simulation.get('grid_import_kwh', 0):,.0f} kWh/Jahr
- **Autarkiegrad: {simulation.get('autonomy_degree_percent', 0):.0f}%**
- **Jährliche Einsparung: {simulation.get('annual_savings_eur', 0):,.0f} €**
- **Amortisationszeit: {simulation.get('payback_period_years', 0):.1f} Jahre**
- Speicher-Zyklen/Jahr: {simulation.get('battery_cycles', 0):.0f}

## AUFGABE
Schreibe einen Angebots-Text mit:
1. Persönlicher Anrede und Bezug zum Standort
2. Zusammenfassung der Systemkonfiguration
3. Hervorhebung der wirtschaftlichen Vorteile (Einsparungen, ROI)
4. Erklärung des Autarkiegrads und was das für den Kunden bedeutet
5. Umweltvorteile (CO2-Einsparung ca. 400g/kWh)
6. Call-to-Action

Länge: 3-4 Absätze, professionell und überzeugend.
"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",  # Oder claude-opus-4-5 wenn verfügbar
                max_tokens=1500,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
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
                import re
                json_match = re.search(r'\[[\s\S]*\]', response_text)
                if json_match:
                    return json.loads(json_match.group())
                return self._fallback_faq()
                
        except Exception as e:
            logger.error(f"Claude FAQ Fehler: {e}")
            return self._fallback_faq()
    
    # ============ FALLBACK METHODS ============
    
    def _fallback_offer_text(self, project: Dict, simulation: Dict) -> str:
        """Fallback wenn Claude nicht verfügbar"""
        return f"""
Sehr geehrte/r {project.get('customer_name', 'Kunde')},

vielen Dank für Ihr Interesse an einer PV-Speicherlösung für Ihr Gewerbeobjekt 
in {project.get('city', project.get('postal_code', ''))}.

**Ihre maßgeschneiderte Systemkonfiguration:**
- PV-Leistung: {project.get('pv_peak_power_kw', 0)} kWp
- Speicherkapazität: {project.get('battery_capacity_kwh', 0)} kWh
- Für Ihren Jahresverbrauch von {project.get('annual_consumption_kwh', 0):,.0f} kWh optimiert

**Ihre Vorteile auf einen Blick:**
- Autarkiegrad: {simulation.get('autonomy_degree_percent', 0):.0f}% – Sie decken einen Großteil 
  Ihres Strombedarfs selbst
- Jährliche Einsparung: {simulation.get('annual_savings_eur', 0):,.0f} € durch reduzierten 
  Netzbezug und Einspeisevergütung
- Amortisationszeit: {simulation.get('payback_period_years', 0):.1f} Jahre
- CO₂-Einsparung: ca. {simulation.get('pv_generation_kwh', 0) * 0.4 / 1000:.1f} Tonnen pro Jahr

Mit diesem System machen Sie sich unabhängiger von steigenden Strompreisen und 
leisten gleichzeitig einen wichtigen Beitrag zum Klimaschutz.

Gerne erstellen wir Ihnen ein detailliertes Angebot mit konkreten Komponenten 
und Installationskosten. Kontaktieren Sie uns für eine persönliche Beratung.

Mit freundlichen Grüßen,
Ihr EWS Team
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


# Singleton Instance
_claude_service: Optional[ClaudeService] = None

def get_claude_service() -> ClaudeService:
    """Get or create Claude service instance"""
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeService()
    return _claude_service
