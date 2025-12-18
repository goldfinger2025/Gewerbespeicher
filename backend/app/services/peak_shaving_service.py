"""
Peak-Shaving Service für Gewerbespeicher
=========================================

Berechnet das Einsparpotenzial durch Lastspitzenkappung mit Batteriespeichern.

Für Gewerbekunden mit > 100.000 kWh/Jahr Verbrauch ist dies oft der
WICHTIGSTE Wirtschaftlichkeitsfaktor!

Hintergrund:
- Ab 100 MWh/Jahr erfolgt 15-Minuten-Leistungsmessung (RLM)
- Die höchste Lastspitze des Jahres bestimmt den Leistungspreis
- Leistungspreise variieren regional: 60-440 €/kW/Jahr
- Selbst kurze Lastspitzen (z.B. Maschinenanläufe) können teuer werden

Stand: Dezember 2025
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

from app.config import LEISTUNGSPREISE_EUR_KW_JAHR, NETZENTGELT_SCHWELLEN

logger = logging.getLogger(__name__)


@dataclass
class PeakShavingResult:
    """Ergebnis der Peak-Shaving-Analyse"""
    original_peak_kw: float
    reduced_peak_kw: float
    peak_reduction_kw: float
    annual_savings_eur: float
    required_battery_kwh: float
    required_battery_power_kw: float
    roi_years: float
    top_peaks: List[Dict]
    shaving_events_per_year: int
    total_shaved_energy_kwh: float


class PeakShavingService:
    """
    Service zur Analyse und Berechnung von Peak-Shaving-Potenzialen

    Peak-Shaving ist die Reduktion von Lastspitzen durch:
    1. Batterieentladung während Spitzenlast
    2. Lastverschiebung (wenn möglich)
    3. PV-Eigenverbrauchsoptimierung

    Für Gewerbekunden ist dies oft wirtschaftlicher als reine
    Eigenverbrauchsoptimierung!
    """

    def __init__(
        self,
        leistungspreis_eur_kw: float = None,
        leistungspreis_kategorie: str = "mittel"
    ):
        """
        Initialisiert den Peak-Shaving-Service

        Args:
            leistungspreis_eur_kw: Spezifischer Leistungspreis (€/kW/Jahr)
            leistungspreis_kategorie: Kategorie wenn kein spezifischer Preis
                                      ("niedrig", "mittel", "hoch", "sehr_hoch", "extrem")
        """
        if leistungspreis_eur_kw is not None:
            self.leistungspreis = leistungspreis_eur_kw
        else:
            self.leistungspreis = LEISTUNGSPREISE_EUR_KW_JAHR.get(
                leistungspreis_kategorie,
                LEISTUNGSPREISE_EUR_KW_JAHR["default"]
            )

    def analyze_load_profile(
        self,
        load_profile_kw: np.ndarray,
        interval_minutes: int = 15
    ) -> Dict:
        """
        Analysiert ein Lastprofil auf Peak-Shaving-Potenzial

        Args:
            load_profile_kw: Array mit Lastwerten in kW
            interval_minutes: Zeitintervall zwischen Messwerten (Standard: 15 Min)

        Returns:
            Dict mit Analyseergebnissen
        """
        if len(load_profile_kw) == 0:
            return {"error": "Leeres Lastprofil"}

        # Grundlegende Statistiken
        max_load = float(np.max(load_profile_kw))
        min_load = float(np.min(load_profile_kw))
        mean_load = float(np.mean(load_profile_kw))
        std_load = float(np.std(load_profile_kw))

        # Berechne Benutzungsstunden
        hours_per_interval = interval_minutes / 60
        total_hours = len(load_profile_kw) * hours_per_interval
        total_energy_kwh = float(np.sum(load_profile_kw) * hours_per_interval)

        benutzungsstunden = total_energy_kwh / max_load if max_load > 0 else 0

        # Identifiziere Spitzenlasten (> 90. Perzentil)
        p90 = np.percentile(load_profile_kw, 90)
        peak_indices = np.where(load_profile_kw > p90)[0]

        # Berechne Peak-Shaving-Potenzial
        potential_reduction = max_load - p90
        potential_savings = potential_reduction * self.leistungspreis

        # Peak-Shaving empfohlen?
        is_recommended = (
            total_energy_kwh >= NETZENTGELT_SCHWELLEN["rlm_messung_ab_kwh"] and
            potential_savings > 1000  # Mindestens 1000€/Jahr Ersparnis sinnvoll
        )

        return {
            "lastprofil_statistik": {
                "max_kw": round(max_load, 2),
                "min_kw": round(min_load, 2),
                "mittel_kw": round(mean_load, 2),
                "standardabweichung_kw": round(std_load, 2),
            },
            "energie": {
                "jahresverbrauch_kwh": round(total_energy_kwh, 0),
                "benutzungsstunden": round(benutzungsstunden, 0),
            },
            "peak_analyse": {
                "p90_kw": round(p90, 2),
                "anzahl_peaks_ueber_p90": len(peak_indices),
                "peak_reduktion_potential_kw": round(potential_reduction, 2),
                "geschaetzte_ersparnis_eur": round(potential_savings, 0),
            },
            "empfehlung": {
                "peak_shaving_empfohlen": is_recommended,
                "rlm_messung": total_energy_kwh >= NETZENTGELT_SCHWELLEN["rlm_messung_ab_kwh"],
                "leistungspreis_eur_kw": self.leistungspreis,
            }
        }

    def identify_top_peaks(
        self,
        load_profile_kw: np.ndarray,
        n_peaks: int = 10,
        interval_minutes: int = 15,
        min_distance_hours: float = 4.0
    ) -> List[Dict]:
        """
        Identifiziert die Top-N Lastspitzen im Profil

        Args:
            load_profile_kw: Lastprofil in kW
            n_peaks: Anzahl der zu identifizierenden Spitzen
            interval_minutes: Zeitintervall
            min_distance_hours: Mindestabstand zwischen Peaks in Stunden

        Returns:
            Liste der Top-Peaks mit Details
        """
        intervals_per_hour = 60 / interval_minutes
        min_distance = int(min_distance_hours * intervals_per_hour)

        peaks = []
        profile_copy = load_profile_kw.copy()

        for _ in range(n_peaks):
            if np.max(profile_copy) <= 0:
                break

            peak_idx = int(np.argmax(profile_copy))
            peak_value = float(profile_copy[peak_idx])

            # Berechne Zeitpunkt (angenommen Start 01.01. 00:00)
            hour_of_year = peak_idx / intervals_per_hour
            day_of_year = int(hour_of_year // 24) + 1
            hour_of_day = hour_of_year % 24
            month = (day_of_year - 1) // 30 + 1  # Vereinfacht

            peaks.append({
                "rang": len(peaks) + 1,
                "index": peak_idx,
                "leistung_kw": round(peak_value, 2),
                "tag_im_jahr": day_of_year,
                "monat": int(min(month, 12)),
                "uhrzeit": f"{int(hour_of_day):02d}:{int((hour_of_day % 1) * 60):02d}",
                "potenzielle_kosten_eur": round(peak_value * self.leistungspreis, 0),
            })

            # Lösche Peak und Umgebung für nächste Iteration
            start = max(0, peak_idx - min_distance)
            end = min(len(profile_copy), peak_idx + min_distance)
            profile_copy[start:end] = 0

        return peaks

    def calculate_required_battery(
        self,
        load_profile_kw: np.ndarray,
        target_peak_kw: float,
        interval_minutes: int = 15,
        battery_efficiency: float = 0.95,
        max_soc: float = 0.9,
        min_soc: float = 0.1
    ) -> Dict:
        """
        Berechnet die benötigte Batteriegröße für ein Peak-Shaving-Ziel

        Args:
            load_profile_kw: Lastprofil in kW
            target_peak_kw: Ziel-Maximalleistung nach Peak-Shaving
            interval_minutes: Zeitintervall
            battery_efficiency: Entlade-Effizienz
            max_soc: Maximaler Ladezustand
            min_soc: Minimaler Ladezustand

        Returns:
            Dict mit Batterie-Anforderungen
        """
        usable_soc_range = max_soc - min_soc
        hours_per_interval = interval_minutes / 60

        # Analysiere jeden Peak über dem Ziel
        shaving_events = []
        total_shaved_energy = 0
        max_shaving_power = 0
        max_consecutive_energy = 0

        current_event_energy = 0
        in_event = False

        for i, load in enumerate(load_profile_kw):
            if load > target_peak_kw:
                shaving_needed = load - target_peak_kw
                shaving_power = shaving_needed / battery_efficiency
                energy_needed = shaving_power * hours_per_interval

                total_shaved_energy += energy_needed
                max_shaving_power = max(max_shaving_power, shaving_power)
                current_event_energy += energy_needed

                if not in_event:
                    in_event = True
            else:
                if in_event:
                    # Event beendet
                    max_consecutive_energy = max(max_consecutive_energy, current_event_energy)
                    shaving_events.append({
                        "end_index": i,
                        "energy_kwh": round(current_event_energy, 2)
                    })
                    current_event_energy = 0
                    in_event = False

        # Letztes Event abschließen
        if in_event:
            max_consecutive_energy = max(max_consecutive_energy, current_event_energy)
            shaving_events.append({
                "end_index": len(load_profile_kw),
                "energy_kwh": round(current_event_energy, 2)
            })

        # Berechne Batteriegröße
        # Kapazität muss größte zusammenhängende Shaving-Periode abdecken
        required_capacity_kwh = max_consecutive_energy / usable_soc_range if usable_soc_range > 0 else 0
        required_power_kw = max_shaving_power

        # Sicherheitsfaktor
        safety_factor = 1.15
        required_capacity_kwh *= safety_factor
        required_power_kw *= safety_factor

        return {
            "benoetigte_kapazitaet_kwh": round(required_capacity_kwh, 1),
            "benoetigte_leistung_kw": round(required_power_kw, 1),
            "c_rate": round(required_power_kw / required_capacity_kwh, 2) if required_capacity_kwh > 0 else 0,
            "anzahl_shaving_events": len(shaving_events),
            "gesamt_shaving_energie_kwh": round(total_shaved_energy, 1),
            "max_einzelereignis_kwh": round(max_consecutive_energy, 1),
            "sicherheitsfaktor": safety_factor,
        }

    def calculate_peak_shaving_economics(
        self,
        original_peak_kw: float,
        target_peak_kw: float,
        battery_capacity_kwh: float,
        battery_power_kw: float,
        battery_cost_per_kwh: float = 600.0,
        additional_costs: float = 3000.0
    ) -> Dict:
        """
        Berechnet die Wirtschaftlichkeit einer Peak-Shaving-Lösung

        Args:
            original_peak_kw: Ursprüngliche Lastspitze
            target_peak_kw: Ziel-Lastspitze
            battery_capacity_kwh: Batteriekapazität
            battery_power_kw: Batterieleistung
            battery_cost_per_kwh: Batteriekosten pro kWh
            additional_costs: Zusätzliche Kosten (Installation, etc.)

        Returns:
            Dict mit Wirtschaftlichkeitsanalyse
        """
        # Investitionskosten
        battery_cost = battery_capacity_kwh * battery_cost_per_kwh
        total_investment = battery_cost + additional_costs

        # Jährliche Einsparung durch Peak-Shaving
        peak_reduction = original_peak_kw - target_peak_kw
        annual_leistungspreis_savings = peak_reduction * self.leistungspreis

        # ROI
        if annual_leistungspreis_savings > 0:
            simple_payback_years = total_investment / annual_leistungspreis_savings
        else:
            simple_payback_years = 99

        # NPV über 15 Jahre (typische Speicherlebensdauer)
        discount_rate = 0.03
        years = 15
        npv = -total_investment
        for year in range(1, years + 1):
            npv += annual_leistungspreis_savings / ((1 + discount_rate) ** year)

        # ROI
        total_savings_15y = annual_leistungspreis_savings * years
        roi_percent = ((total_savings_15y - total_investment) / total_investment) * 100 if total_investment > 0 else 0

        return {
            "investition": {
                "batterie_kosten_eur": round(battery_cost, 0),
                "zusatzkosten_eur": round(additional_costs, 0),
                "gesamt_investition_eur": round(total_investment, 0),
            },
            "peak_reduktion": {
                "original_peak_kw": round(original_peak_kw, 1),
                "ziel_peak_kw": round(target_peak_kw, 1),
                "reduktion_kw": round(peak_reduction, 1),
                "reduktion_prozent": round((peak_reduction / original_peak_kw) * 100, 1) if original_peak_kw > 0 else 0,
            },
            "jaehrliche_ersparnis": {
                "leistungspreis_ersparnis_eur": round(annual_leistungspreis_savings, 0),
                "leistungspreis_eur_kw": self.leistungspreis,
            },
            "wirtschaftlichkeit": {
                "amortisation_jahre": round(simple_payback_years, 1),
                "npv_15_jahre_eur": round(npv, 0),
                "roi_15_jahre_prozent": round(roi_percent, 1),
                "ersparnis_15_jahre_eur": round(total_savings_15y, 0),
            },
            "empfehlung": self._generate_recommendation(
                simple_payback_years,
                annual_leistungspreis_savings,
                total_investment
            )
        }

    def simulate_peak_shaving(
        self,
        load_profile_kw: np.ndarray,
        battery_capacity_kwh: float,
        battery_power_kw: float,
        target_peak_kw: float,
        interval_minutes: int = 15,
        charge_efficiency: float = 0.95,
        discharge_efficiency: float = 0.95,
        initial_soc: float = 0.5
    ) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Simuliert Peak-Shaving-Betrieb über ein Jahr

        Strategie: Batterie lädt in Niedriglast-Zeiten und
        entlädt bei Überschreitung der Ziellast.

        Returns:
            Tuple von (modifiziertes Lastprofil, SOC-Verlauf, Statistiken)
        """
        hours_per_interval = interval_minutes / 60
        n_intervals = len(load_profile_kw)

        min_soc = battery_capacity_kwh * 0.1
        max_soc = battery_capacity_kwh * 0.9
        current_soc = battery_capacity_kwh * initial_soc

        modified_load = np.copy(load_profile_kw)
        soc_profile = np.zeros(n_intervals)

        total_discharged = 0
        total_charged = 0
        shaving_events = 0

        # Berechne Lade-Schwelle (z.B. 50% der Ziellast)
        charge_threshold = target_peak_kw * 0.5

        for i in range(n_intervals):
            original_load = load_profile_kw[i]

            if original_load > target_peak_kw:
                # ENTLADEN: Lastspitze kappen
                needed_reduction = original_load - target_peak_kw
                max_discharge = min(
                    needed_reduction,
                    battery_power_kw,
                    (current_soc - min_soc) * discharge_efficiency / hours_per_interval
                )

                if max_discharge > 0:
                    actual_discharge = max_discharge
                    current_soc -= actual_discharge * hours_per_interval / discharge_efficiency
                    modified_load[i] = original_load - actual_discharge
                    total_discharged += actual_discharge * hours_per_interval
                    shaving_events += 1

            elif original_load < charge_threshold and current_soc < max_soc:
                # LADEN: In Niedriglast-Zeiten nachladen
                available_headroom = target_peak_kw - original_load
                max_charge = min(
                    available_headroom,
                    battery_power_kw,
                    (max_soc - current_soc) / charge_efficiency / hours_per_interval
                )

                if max_charge > 0:
                    actual_charge = max_charge
                    current_soc += actual_charge * hours_per_interval * charge_efficiency
                    modified_load[i] = original_load + actual_charge
                    total_charged += actual_charge * hours_per_interval

            soc_profile[i] = current_soc

        # Statistiken
        original_peak = float(np.max(load_profile_kw))
        achieved_peak = float(np.max(modified_load))

        stats = {
            "original_peak_kw": round(original_peak, 2),
            "erreichter_peak_kw": round(achieved_peak, 2),
            "peak_reduktion_kw": round(original_peak - achieved_peak, 2),
            "ziel_erreicht": achieved_peak <= target_peak_kw * 1.01,  # 1% Toleranz
            "entladungen_kwh": round(total_discharged, 1),
            "ladungen_kwh": round(total_charged, 1),
            "shaving_events": shaving_events,
            "durchschnittlicher_soc": round(float(np.mean(soc_profile)) / battery_capacity_kwh * 100, 1),
        }

        return modified_load, soc_profile, stats

    def full_analysis(
        self,
        load_profile_kw: np.ndarray,
        battery_capacity_kwh: float,
        battery_power_kw: float,
        interval_minutes: int = 15,
        battery_cost_per_kwh: float = 600.0
    ) -> Dict:
        """
        Führt eine vollständige Peak-Shaving-Analyse durch

        Args:
            load_profile_kw: Jahres-Lastprofil in kW
            battery_capacity_kwh: Verfügbare Batteriekapazität
            battery_power_kw: Verfügbare Batterieleistung
            interval_minutes: Messintervall
            battery_cost_per_kwh: Batteriekosten

        Returns:
            Umfassende Analyse mit Empfehlungen
        """
        # 1. Lastprofil analysieren
        profile_analysis = self.analyze_load_profile(load_profile_kw, interval_minutes)

        # 2. Top-Peaks identifizieren
        top_peaks = self.identify_top_peaks(load_profile_kw, n_peaks=10, interval_minutes=interval_minutes)

        original_peak = profile_analysis["lastprofil_statistik"]["max_kw"]

        # 3. Verschiedene Ziel-Peaks analysieren (10%, 20%, 30% Reduktion)
        scenarios = []
        for reduction_pct in [0.10, 0.20, 0.30]:
            target_peak = original_peak * (1 - reduction_pct)

            # Batterie-Anforderungen
            battery_req = self.calculate_required_battery(
                load_profile_kw, target_peak, interval_minutes
            )

            # Prüfen ob aktuelle Batterie ausreicht
            battery_sufficient = (
                battery_capacity_kwh >= battery_req["benoetigte_kapazitaet_kwh"] and
                battery_power_kw >= battery_req["benoetigte_leistung_kw"]
            )

            # Wirtschaftlichkeit berechnen
            economics = self.calculate_peak_shaving_economics(
                original_peak,
                target_peak,
                battery_req["benoetigte_kapazitaet_kwh"],
                battery_req["benoetigte_leistung_kw"],
                battery_cost_per_kwh
            )

            scenarios.append({
                "reduktion_prozent": int(reduction_pct * 100),
                "ziel_peak_kw": round(target_peak, 1),
                "batterie_ausreichend": battery_sufficient,
                "batterie_anforderung": battery_req,
                "wirtschaftlichkeit": economics["wirtschaftlichkeit"],
                "jaehrliche_ersparnis_eur": economics["jaehrliche_ersparnis"]["leistungspreis_ersparnis_eur"],
            })

        # 4. Simulation mit aktueller Batterie
        best_target = original_peak * 0.8  # Versuche 20% Reduktion
        modified_load, soc, sim_stats = self.simulate_peak_shaving(
            load_profile_kw,
            battery_capacity_kwh,
            battery_power_kw,
            best_target,
            interval_minutes
        )

        return {
            "zusammenfassung": {
                "original_peak_kw": original_peak,
                "jahresverbrauch_kwh": profile_analysis["energie"]["jahresverbrauch_kwh"],
                "benutzungsstunden": profile_analysis["energie"]["benutzungsstunden"],
                "rlm_messung": profile_analysis["empfehlung"]["rlm_messung"],
                "leistungspreis_eur_kw": self.leistungspreis,
                "peak_shaving_empfohlen": profile_analysis["empfehlung"]["peak_shaving_empfohlen"],
            },
            "top_peaks": top_peaks[:5],  # Nur Top 5 für Übersicht
            "szenarien": scenarios,
            "simulation": sim_stats,
            "empfehlung": self._get_best_scenario_recommendation(scenarios),
        }

    def _generate_recommendation(
        self,
        payback_years: float,
        annual_savings: float,
        investment: float
    ) -> str:
        """Generiert Empfehlungstext"""
        if payback_years < 5:
            return "SEHR EMPFEHLENSWERT: Schnelle Amortisation unter 5 Jahren. Peak-Shaving ist wirtschaftlich sehr attraktiv."
        elif payback_years < 8:
            return "EMPFEHLENSWERT: Gute Amortisation unter 8 Jahren. Peak-Shaving lohnt sich wirtschaftlich."
        elif payback_years < 12:
            return "BEDINGT EMPFEHLENSWERT: Amortisation unter 12 Jahren. Weitere Anwendungsfälle (Eigenverbrauch, Notstrom) einbeziehen."
        else:
            return "EINGESCHRÄNKT: Lange Amortisation. Peak-Shaving allein rechtfertigt die Investition möglicherweise nicht."

    def _get_best_scenario_recommendation(self, scenarios: List[Dict]) -> Dict:
        """Wählt das beste Szenario aus"""
        best = None
        best_score = -1

        for scenario in scenarios:
            # Score basiert auf Amortisation und Ersparnis
            payback = scenario["wirtschaftlichkeit"]["amortisation_jahre"]
            savings = scenario["jaehrliche_ersparnis_eur"]

            if payback < 99:
                score = savings / payback  # €/Jahr pro Amortisationsjahr
                if score > best_score:
                    best_score = score
                    best = scenario

        if best:
            return {
                "empfohlenes_szenario": f"{best['reduktion_prozent']}% Reduktion",
                "ziel_peak_kw": best["ziel_peak_kw"],
                "jaehrliche_ersparnis_eur": best["jaehrliche_ersparnis_eur"],
                "amortisation_jahre": best["wirtschaftlichkeit"]["amortisation_jahre"],
            }
        else:
            return {
                "empfohlenes_szenario": "Peak-Shaving wirtschaftlich nicht empfohlen",
                "grund": "Keine ausreichende Ersparnis erzielbar"
            }


# Singleton für einfachen Zugriff
_peak_shaving_service: Optional[PeakShavingService] = None


def get_peak_shaving_service(
    leistungspreis_eur_kw: float = None,
    leistungspreis_kategorie: str = "mittel"
) -> PeakShavingService:
    """Gibt Peak-Shaving-Service-Instanz zurück"""
    global _peak_shaving_service
    if _peak_shaving_service is None or leistungspreis_eur_kw is not None:
        _peak_shaving_service = PeakShavingService(
            leistungspreis_eur_kw=leistungspreis_eur_kw,
            leistungspreis_kategorie=leistungspreis_kategorie
        )
    return _peak_shaving_service
