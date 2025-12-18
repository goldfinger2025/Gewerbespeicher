"""
Emergency Power Service (Notstromberechnung) für Gewerbespeicher
================================================================

Berechnet Notstromkapazität und simuliert Netzausfälle für Gewerbekunden.

Für Gewerbekunden ist Notstrom ein wichtiges Verkaufsargument:
- Betriebssicherheit bei Netzausfällen
- Schutz kritischer Lasten (Kühlungen, Server, Pumpen)
- Reduzierung von Betriebsunterbrechungsrisiken
- Versicherungsrelevante Absicherung

Stand: Dezember 2025
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CriticalLoad:
    """Kritische Last für Notstromversorgung"""
    name: str
    power_kw: float
    priority: int  # 1 = höchste Priorität
    min_runtime_hours: float  # Minimale Laufzeit die gewährleistet sein muss
    can_be_shed: bool = False  # Kann bei Knappheit abgeschaltet werden


@dataclass
class BlackoutSimulationResult:
    """Ergebnis einer Blackout-Simulation"""
    survived: bool
    duration_hours: float
    critical_loads_supplied_hours: float
    energy_consumed_kwh: float
    final_soc_percent: float
    load_shedding_events: int
    pv_contribution_kwh: float


class EmergencyPowerService:
    """
    Service zur Berechnung und Simulation von Notstromversorgung

    Notstrom-Szenarien für Gewerbekunden:
    1. Kurze Ausfälle (< 1h): Überbrückung bis Netz wieder da
    2. Mittlere Ausfälle (1-4h): Kritische Lasten versorgen
    3. Lange Ausfälle (> 4h): Mit PV-Unterstützung durchhalten
    """

    # Typische Ausfallstatistiken Deutschland (SAIDI)
    OUTAGE_STATISTICS = {
        "durchschnittliche_dauer_min": 12.2,  # SAIDI 2023
        "ausfaelle_pro_jahr": 0.32,  # SAIFI
        "max_typisch_stunden": 4,  # 95% aller Ausfälle
        "extremereignis_stunden": 24,  # Sturmschäden etc.
    }

    # Typische kritische Lasten für Gewerbe
    TYPICAL_CRITICAL_LOADS = {
        "kuehlanlage": {"power_kw": 5.0, "priority": 1, "min_runtime_hours": 4},
        "server_it": {"power_kw": 2.0, "priority": 1, "min_runtime_hours": 2},
        "notbeleuchtung": {"power_kw": 0.5, "priority": 1, "min_runtime_hours": 8},
        "alarm_sicherheit": {"power_kw": 0.3, "priority": 1, "min_runtime_hours": 24},
        "pumpen": {"power_kw": 3.0, "priority": 2, "min_runtime_hours": 2},
        "lueftung": {"power_kw": 4.0, "priority": 3, "min_runtime_hours": 1},
        "produktionsmaschine": {"power_kw": 15.0, "priority": 4, "min_runtime_hours": 0.5},
    }

    def __init__(
        self,
        discharge_efficiency: float = 0.95,
        min_soc: float = 0.10,
        max_soc: float = 0.90
    ):
        """
        Initialisiert den Notstrom-Service

        Args:
            discharge_efficiency: Entladeeffizienz der Batterie
            min_soc: Minimaler Ladezustand (für Notstrom oft 10%)
            max_soc: Maximaler Ladezustand
        """
        self.discharge_efficiency = discharge_efficiency
        self.min_soc = min_soc
        self.max_soc = max_soc

    def calculate_backup_capacity(
        self,
        critical_loads_kw: List[float],
        required_hours: float,
        safety_factor: float = 1.2
    ) -> Dict:
        """
        Berechnet die benötigte Batteriekapazität für Notstromversorgung

        Args:
            critical_loads_kw: Liste der kritischen Lasten in kW
            required_hours: Gewünschte Backup-Dauer in Stunden
            safety_factor: Sicherheitsfaktor (Standard: 20%)

        Returns:
            Dict mit Kapazitätsanforderungen
        """
        total_load_kw = sum(critical_loads_kw)

        # Energiebedarf berechnen
        energy_required_kwh = total_load_kw * required_hours

        # Verluste durch Effizienz berücksichtigen
        energy_with_losses = energy_required_kwh / self.discharge_efficiency

        # Nutzbare Kapazität (80% bei 10-90% SOC)
        usable_soc_range = self.max_soc - self.min_soc

        # Brutto-Kapazität berechnen
        gross_capacity_kwh = energy_with_losses / usable_soc_range

        # Sicherheitsfaktor anwenden
        recommended_capacity_kwh = gross_capacity_kwh * safety_factor

        # Benötigte Leistung = höchste Last + Reserve
        required_power_kw = total_load_kw * 1.1  # 10% Reserve

        return {
            "kritische_lasten": {
                "anzahl": len(critical_loads_kw),
                "gesamt_kw": round(total_load_kw, 2),
                "einzellasten_kw": [round(load, 2) for load in critical_loads_kw],
            },
            "anforderungen": {
                "backup_dauer_stunden": required_hours,
                "energiebedarf_kwh": round(energy_required_kwh, 1),
                "mit_verlusten_kwh": round(energy_with_losses, 1),
            },
            "batterie_empfehlung": {
                "mindestkapazitaet_kwh": round(gross_capacity_kwh, 1),
                "empfohlene_kapazitaet_kwh": round(recommended_capacity_kwh, 1),
                "mindestleistung_kw": round(required_power_kw, 1),
                "sicherheitsfaktor": safety_factor,
            },
            "hinweise": self._generate_backup_hints(
                total_load_kw, required_hours, recommended_capacity_kwh
            )
        }

    def check_backup_capability(
        self,
        battery_capacity_kwh: float,
        battery_power_kw: float,
        critical_loads_kw: List[float],
        required_hours: float,
        current_soc: float = 0.9
    ) -> Dict:
        """
        Prüft ob eine vorhandene Batterie die Notstrom-Anforderungen erfüllt

        Args:
            battery_capacity_kwh: Vorhandene Batteriekapazität
            battery_power_kw: Vorhandene Batterieleistung
            critical_loads_kw: Kritische Lasten
            required_hours: Gewünschte Backup-Dauer
            current_soc: Aktueller Ladezustand (0-1)

        Returns:
            Dict mit Prüfergebnis
        """
        total_load_kw = sum(critical_loads_kw)

        # Prüfe Leistung
        power_sufficient = battery_power_kw >= total_load_kw
        power_margin_kw = battery_power_kw - total_load_kw

        # Verfügbare Energie berechnen
        usable_capacity = battery_capacity_kwh * (current_soc - self.min_soc)
        usable_energy = usable_capacity * self.discharge_efficiency

        # Tatsächliche Backup-Zeit berechnen
        if total_load_kw > 0:
            actual_backup_hours = usable_energy / total_load_kw
        else:
            actual_backup_hours = float('inf')

        duration_sufficient = actual_backup_hours >= required_hours

        # Gesamtbewertung
        overall_sufficient = power_sufficient and duration_sufficient

        # Fehlende Kapazität berechnen
        if not duration_sufficient:
            missing_energy = (required_hours - actual_backup_hours) * total_load_kw
            missing_capacity = missing_energy / self.discharge_efficiency / (self.max_soc - self.min_soc)
        else:
            missing_capacity = 0

        return {
            "pruefung": {
                "notstrom_faehig": overall_sufficient,
                "leistung_ausreichend": power_sufficient,
                "dauer_ausreichend": duration_sufficient,
            },
            "leistung": {
                "benoetigte_kw": round(total_load_kw, 2),
                "verfuegbare_kw": round(battery_power_kw, 2),
                "reserve_kw": round(power_margin_kw, 2),
            },
            "dauer": {
                "benoetigte_stunden": required_hours,
                "erreichbare_stunden": round(actual_backup_hours, 1),
                "aktueller_soc_prozent": round(current_soc * 100, 0),
            },
            "erweiterung": {
                "zusaetzliche_kapazitaet_kwh": round(missing_capacity, 1) if missing_capacity > 0 else 0,
                "empfehlung": self._generate_upgrade_recommendation(
                    power_sufficient, duration_sufficient, missing_capacity, power_margin_kw
                )
            }
        }

    def simulate_blackout(
        self,
        load_profile_kw: np.ndarray,
        battery_capacity_kwh: float,
        battery_power_kw: float,
        critical_loads_kw: float,
        outage_start_hour: int,
        outage_duration_hours: int,
        pv_profile_kw: Optional[np.ndarray] = None,
        initial_soc: float = 0.8,
        interval_minutes: int = 15
    ) -> Dict:
        """
        Simuliert einen Netzausfall und prüft ob kritische Lasten versorgt werden

        Args:
            load_profile_kw: Normales Lastprofil (für Kontext)
            battery_capacity_kwh: Batteriekapazität
            battery_power_kw: Batterieleistung
            critical_loads_kw: Gesamtleistung kritischer Lasten
            outage_start_hour: Stunde des Ausfallbeginns (0-8759)
            outage_duration_hours: Dauer des Ausfalls
            pv_profile_kw: Optional - PV-Erzeugungsprofil
            initial_soc: SOC bei Ausfallbeginn
            interval_minutes: Zeitintervall

        Returns:
            Dict mit Simulationsergebnis
        """
        intervals_per_hour = 60 / interval_minutes
        outage_intervals = int(outage_duration_hours * intervals_per_hour)
        start_interval = int(outage_start_hour * intervals_per_hour)

        # SOC in kWh
        current_soc_kwh = battery_capacity_kwh * initial_soc
        min_soc_kwh = battery_capacity_kwh * self.min_soc

        # Simulation
        soc_profile = []
        load_served = []
        pv_used = []
        load_shedding_events = 0
        total_energy_consumed = 0
        total_pv_contribution = 0

        hours_per_interval = interval_minutes / 60

        for i in range(outage_intervals):
            interval_idx = start_interval + i

            # PV-Erzeugung in diesem Intervall
            pv_available = 0
            if pv_profile_kw is not None and interval_idx < len(pv_profile_kw):
                pv_available = pv_profile_kw[interval_idx]

            # Netto-Last (kritische Last minus PV)
            net_load = max(0, critical_loads_kw - pv_available)

            # Prüfe ob Leistung ausreicht
            if net_load > battery_power_kw:
                net_load = battery_power_kw
                load_shedding_events += 1

            # Energie aus Batterie entnehmen
            energy_needed = net_load * hours_per_interval / self.discharge_efficiency

            # Prüfe ob genug Kapazität
            if current_soc_kwh - energy_needed < min_soc_kwh:
                # Batterie leer - Load Shedding
                available_energy = (current_soc_kwh - min_soc_kwh) * self.discharge_efficiency
                actual_load_served = available_energy / hours_per_interval
                current_soc_kwh = min_soc_kwh
                load_shedding_events += 1
            else:
                current_soc_kwh -= energy_needed
                actual_load_served = net_load

            soc_profile.append(current_soc_kwh / battery_capacity_kwh * 100)
            load_served.append(actual_load_served)
            pv_used.append(min(pv_available, critical_loads_kw))
            total_energy_consumed += actual_load_served * hours_per_interval
            total_pv_contribution += min(pv_available, critical_loads_kw) * hours_per_interval

        # Ergebnis
        final_soc = current_soc_kwh / battery_capacity_kwh
        survived = final_soc > self.min_soc and load_shedding_events == 0

        avg_load_served = np.mean(load_served) if load_served else 0
        critical_loads_supplied_ratio = avg_load_served / critical_loads_kw if critical_loads_kw > 0 else 1

        return {
            "ergebnis": {
                "ausfall_ueberbrueckt": survived,
                "bewertung": self._rate_blackout_result(survived, load_shedding_events, critical_loads_supplied_ratio),
            },
            "ausfall_details": {
                "start_stunde": outage_start_hour,
                "dauer_stunden": outage_duration_hours,
                "kritische_last_kw": critical_loads_kw,
            },
            "batterie_verlauf": {
                "start_soc_prozent": round(initial_soc * 100, 1),
                "end_soc_prozent": round(final_soc * 100, 1),
                "min_soc_prozent": round(min(soc_profile) if soc_profile else initial_soc * 100, 1),
                "energie_verbraucht_kwh": round(total_energy_consumed, 1),
            },
            "pv_beitrag": {
                "pv_verfuegbar": pv_profile_kw is not None,
                "pv_genutzt_kwh": round(total_pv_contribution, 1),
                "pv_anteil_prozent": round(
                    total_pv_contribution / (total_energy_consumed + total_pv_contribution) * 100
                    if (total_energy_consumed + total_pv_contribution) > 0 else 0, 1
                ),
            },
            "versorgung": {
                "load_shedding_events": load_shedding_events,
                "durchschnittliche_versorgung_prozent": round(critical_loads_supplied_ratio * 100, 1),
            },
            "empfehlung": self._generate_blackout_recommendation(
                survived, final_soc, load_shedding_events, outage_duration_hours
            )
        }

    def analyze_emergency_power_scenarios(
        self,
        battery_capacity_kwh: float,
        battery_power_kw: float,
        critical_loads: List[Dict],
        pv_kwp: Optional[float] = None
    ) -> Dict:
        """
        Analysiert verschiedene Notstrom-Szenarien

        Args:
            battery_capacity_kwh: Batteriekapazität
            battery_power_kw: Batterieleistung
            critical_loads: Liste von Dicts mit 'name', 'power_kw', 'priority'
            pv_kwp: Optional - PV-Leistung für Tageszeit-Szenarien

        Returns:
            Dict mit Szenario-Analyse
        """
        # Sortiere Lasten nach Priorität
        sorted_loads = sorted(critical_loads, key=lambda x: x.get('priority', 99))

        # Gesamtlast
        total_critical_load = sum(load['power_kw'] for load in critical_loads)

        # Usable capacity
        usable_capacity = battery_capacity_kwh * (self.max_soc - self.min_soc)
        usable_energy = usable_capacity * self.discharge_efficiency

        # Szenarien berechnen
        scenarios = []

        # Szenario 1: Alle kritischen Lasten
        if total_critical_load <= battery_power_kw:
            runtime_all = usable_energy / total_critical_load if total_critical_load > 0 else float('inf')
            scenarios.append({
                "name": "Alle kritischen Lasten",
                "last_kw": round(total_critical_load, 2),
                "laufzeit_stunden": round(runtime_all, 1),
                "machbar": True,
            })
        else:
            scenarios.append({
                "name": "Alle kritischen Lasten",
                "last_kw": round(total_critical_load, 2),
                "laufzeit_stunden": 0,
                "machbar": False,
                "grund": "Batterieleistung zu gering",
            })

        # Szenario 2: Nur Priorität 1
        priority_1_loads = [item for item in sorted_loads if item.get('priority', 99) == 1]
        priority_1_total = sum(item['power_kw'] for item in priority_1_loads)
        if priority_1_total > 0 and priority_1_total <= battery_power_kw:
            runtime_p1 = usable_energy / priority_1_total
            scenarios.append({
                "name": "Nur höchste Priorität",
                "last_kw": round(priority_1_total, 2),
                "lasten": [item['name'] for item in priority_1_loads],
                "laufzeit_stunden": round(runtime_p1, 1),
                "machbar": True,
            })

        # Szenario 3: Minimallast (nur Sicherheit + Notbeleuchtung)
        minimal_load = total_critical_load * 0.3  # Annahme: 30% für Minimalversorgung
        if minimal_load > 0 and minimal_load <= battery_power_kw:
            runtime_min = usable_energy / minimal_load
            scenarios.append({
                "name": "Minimallast (30%)",
                "last_kw": round(minimal_load, 2),
                "laufzeit_stunden": round(runtime_min, 1),
                "machbar": True,
            })

        # PV-Unterstützung Szenarien (nur tagsüber)
        if pv_kwp:
            # Annahme: PV liefert im Schnitt 20% der Peak-Leistung
            avg_pv_output = pv_kwp * 0.2

            # Netto-Last mit PV
            net_load_with_pv = max(0, total_critical_load - avg_pv_output)

            if net_load_with_pv <= battery_power_kw:
                if net_load_with_pv > 0:
                    runtime_with_pv = usable_energy / net_load_with_pv
                else:
                    runtime_with_pv = float('inf')

                scenarios.append({
                    "name": "Mit PV-Unterstützung (tagsüber)",
                    "bruttolast_kw": round(total_critical_load, 2),
                    "pv_beitrag_kw": round(avg_pv_output, 2),
                    "nettolast_kw": round(net_load_with_pv, 2),
                    "laufzeit_stunden": round(min(runtime_with_pv, 12), 1),  # Max 12h Tageslicht
                    "machbar": True,
                    "hinweis": "Bei Sonnenschein während des Ausfalls",
                })

        return {
            "zusammenfassung": {
                "batterie_kapazitaet_kwh": battery_capacity_kwh,
                "batterie_leistung_kw": battery_power_kw,
                "nutzbare_energie_kwh": round(usable_energy, 1),
                "kritische_gesamtlast_kw": round(total_critical_load, 2),
            },
            "kritische_lasten": [
                {
                    "name": item.get('name', 'Unbekannt'),
                    "leistung_kw": item['power_kw'],
                    "prioritaet": item.get('priority', 99),
                }
                for item in sorted_loads
            ],
            "szenarien": scenarios,
            "empfehlung": self._generate_scenario_recommendation(scenarios, total_critical_load, battery_power_kw),
            "statistik_deutschland": self.OUTAGE_STATISTICS,
        }

    def _generate_backup_hints(
        self,
        total_load_kw: float,
        required_hours: float,
        recommended_capacity: float
    ) -> List[str]:
        """Generiert Hinweise für Backup-Kapazität"""
        hints = []

        if required_hours <= 1:
            hints.append("Für kurze Ausfälle (<1h) reicht oft die empfohlene Kapazität")
        elif required_hours <= 4:
            hints.append("4-stündige Backup-Zeit deckt 95% aller Netzausfälle in Deutschland ab")
        else:
            hints.append("Für Langzeit-Backup PV-Unterstützung einplanen")

        if total_load_kw > 50:
            hints.append("Bei hoher Last ggf. Lastmanagement für nicht-kritische Verbraucher implementieren")

        if recommended_capacity > 100:
            hints.append("Große Kapazität: Container-Speicher oder mehrere Module prüfen")

        return hints

    def _generate_upgrade_recommendation(
        self,
        power_ok: bool,
        duration_ok: bool,
        missing_capacity: float,
        power_margin: float
    ) -> str:
        """Generiert Upgrade-Empfehlung"""
        if power_ok and duration_ok:
            if power_margin > 5:
                return "System ist für Notstrom gut dimensioniert mit ausreichender Reserve"
            return "System erfüllt Notstrom-Anforderungen knapp"

        if not power_ok:
            return f"Batterieleistung erhöhen: Mindestens {abs(power_margin):.1f} kW zusätzlich benötigt"

        if not duration_ok:
            return f"Kapazität erweitern: {missing_capacity:.1f} kWh zusätzlich für gewünschte Backup-Dauer"

        return "System prüfen"

    def _rate_blackout_result(
        self,
        survived: bool,
        load_shedding_events: int,
        supply_ratio: float
    ) -> str:
        """Bewertet das Blackout-Simulationsergebnis"""
        if survived and load_shedding_events == 0:
            return "BESTANDEN: Vollständige Versorgung während des Ausfalls"
        elif supply_ratio >= 0.9:
            return "AKZEPTABEL: Geringe Unterbrechungen, >90% Versorgung"
        elif supply_ratio >= 0.5:
            return "KRITISCH: Erhebliche Unterbrechungen, Kapazität erhöhen"
        else:
            return "NICHT BESTANDEN: Unzureichende Notstromversorgung"

    def _generate_blackout_recommendation(
        self,
        survived: bool,
        final_soc: float,
        load_shedding: int,
        duration_hours: float
    ) -> str:
        """Generiert Empfehlung basierend auf Blackout-Simulation"""
        if survived and final_soc > 0.3:
            return f"Batterie ausreichend dimensioniert. {round(final_soc*100)}% Restkapazität nach {duration_hours}h Ausfall."
        elif survived and final_soc > 0.15:
            return "Knapp bestanden. Für längere Ausfälle Kapazität um 30% erhöhen."
        elif load_shedding > 0:
            return f"{load_shedding} Lastabwürfe während Simulation. Leistung und/oder Kapazität erhöhen."
        else:
            return "Batterie unzureichend. Dimensionierung überprüfen."

    def _generate_scenario_recommendation(
        self,
        scenarios: List[Dict],
        total_load: float,
        battery_power: float
    ) -> str:
        """Generiert Empfehlung aus Szenarien"""
        viable_scenarios = [s for s in scenarios if s.get('machbar', False)]

        if not viable_scenarios:
            return "Batterie für Notstrom ungeeignet. Leistung erhöhen oder Lasten reduzieren."

        best = max(viable_scenarios, key=lambda x: x.get('laufzeit_stunden', 0))

        if best['laufzeit_stunden'] >= 4:
            return f"Gute Notstromfähigkeit: '{best['name']}' ermöglicht {best['laufzeit_stunden']:.1f}h Betrieb"
        elif best['laufzeit_stunden'] >= 1:
            return f"Basis-Notstrom möglich: {best['laufzeit_stunden']:.1f}h im Szenario '{best['name']}'"
        else:
            return "Notstrom nur für sehr kurze Ausfälle geeignet. Kapazität erhöhen empfohlen."


# Singleton für einfachen Zugriff
_emergency_power_service: Optional[EmergencyPowerService] = None


def get_emergency_power_service() -> EmergencyPowerService:
    """Gibt Emergency-Power-Service-Instanz zurück"""
    global _emergency_power_service
    if _emergency_power_service is None:
        _emergency_power_service = EmergencyPowerService()
    return _emergency_power_service
