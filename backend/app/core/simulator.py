"""
PV + Storage Simulator
Core simulation engine using simplified physics model
"""

import numpy as np
from typing import Dict

from app.config import SIMULATION_DEFAULTS


class PVStorageSimulator:
    """
    Simulator for PV + Battery Storage Systems
    
    Uses simplified model for MVP, can be extended with pvlib for production.
    """
    
    def __init__(self, latitude: float, longitude: float):
        """
        Initialize simulator with location
        
        Args:
            latitude: Site latitude
            longitude: Site longitude
        """
        self.latitude = latitude
        self.longitude = longitude
    
    async def simulate_year(
        self,
        pv_peak_kw: float,
        battery_kwh: float,
        battery_power_kw: float,
        annual_consumption_kwh: float,
        electricity_price: float = 0.30,
        feed_in_tariff: float = 0.08,
        pv_tilt: float = 30.0,
        year: int = 2024
    ) -> Dict:
        """
        Run full year simulation with hourly resolution
        
        Args:
            pv_peak_kw: PV system peak power in kW
            battery_kwh: Battery capacity in kWh
            battery_power_kw: Battery max charge/discharge power in kW
            annual_consumption_kwh: Annual electricity consumption in kWh
            electricity_price: Electricity price in €/kWh
            feed_in_tariff: Feed-in tariff in €/kWh
            pv_tilt: PV panel tilt angle in degrees
            year: Simulation year
            
        Returns:
            Dict with simulation results
        """
        hours = 8760  # Hours per year
        
        # ============ 1. GENERATE PV OUTPUT ============
        pv_output = self._generate_pv_output(pv_peak_kw, pv_tilt, hours)
        
        # ============ 2. GENERATE LOAD PROFILE ============
        load_profile = self._generate_load_profile(annual_consumption_kwh, hours)
        
        # ============ 3. SIMULATE BATTERY OPERATION ============
        (
            battery_soc,
            battery_charge,
            battery_discharge,
            grid_import,
            grid_export
        ) = self._simulate_battery(
            pv_output=pv_output,
            load_profile=load_profile,
            battery_kwh=battery_kwh,
            battery_power_kw=battery_power_kw
        )
        
        # ============ 4. CALCULATE KPIs ============
        total_pv_generation = float(pv_output.sum())
        total_grid_import = float(grid_import.sum())
        total_grid_export = float(grid_export.sum())
        total_self_consumption = total_pv_generation - total_grid_export
        
        # Autarkiegrad: Anteil des Verbrauchs aus eigener Erzeugung
        autonomy_degree = 0
        if annual_consumption_kwh > 0:
            autonomy_degree = (total_self_consumption / annual_consumption_kwh) * 100
            autonomy_degree = min(autonomy_degree, 100)  # Cap at 100%
        
        # Eigenverbrauchsquote: Anteil der PV-Erzeugung, die selbst verbraucht wird
        self_consumption_ratio = 0
        if total_pv_generation > 0:
            self_consumption_ratio = (total_self_consumption / total_pv_generation) * 100
        
        # Battery cycles
        battery_cycles = float(battery_discharge.sum() / battery_kwh) if battery_kwh > 0 else 0

        # Betriebsstunden: Stunden mit Lade- oder Entladeaktivität
        battery_charging_hours = int(np.sum(battery_charge > 0))
        battery_discharging_hours = int(np.sum(battery_discharge > 0))
        battery_operating_hours = battery_charging_hours + battery_discharging_hours

        # Volllaststunden (VDI 4655, IEA PVPS)
        total_battery_discharge = float(battery_discharge.sum())
        pv_full_load_hours = total_pv_generation / pv_peak_kw if pv_peak_kw > 0 else 0
        battery_full_load_hours = total_battery_discharge / battery_power_kw if battery_power_kw > 0 else 0
        battery_utilization_percent = (battery_operating_hours / hours) * 100
        # Kapazitätsfaktor: Verhältnis tatsächlicher zu theoretisch max. Energiedurchsatz
        battery_capacity_factor_percent = (battery_full_load_hours / hours) * 100
        
        # ============ 5. FINANCIAL CALCULATIONS ============
        
        # Kosten ohne Anlage (Referenz)
        cost_without_system = annual_consumption_kwh * electricity_price
        
        # Kosten mit Anlage
        cost_grid_import = total_grid_import * electricity_price
        revenue_feed_in = total_grid_export * feed_in_tariff
        cost_with_system = cost_grid_import - revenue_feed_in
        
        # Jährliche Einsparung
        annual_savings = cost_without_system - cost_with_system
        
        # Investitionskosten (Schätzung)
        pv_cost = pv_peak_kw * 1000  # ~1000 €/kWp
        battery_cost = battery_kwh * 500  # ~500 €/kWh
        installation_cost = (pv_cost + battery_cost) * 0.15  # 15% Installation
        total_investment = pv_cost + battery_cost + installation_cost
        
        # Amortisationszeit
        payback_years = 999
        if annual_savings > 0:
            payback_years = total_investment / annual_savings
        
        return {
            "pv_generation_kwh": round(total_pv_generation, 2),
            "self_consumption_kwh": round(total_self_consumption, 2),
            "grid_import_kwh": round(total_grid_import, 2),
            "grid_export_kwh": round(total_grid_export, 2),
            "autonomy_degree_percent": round(autonomy_degree, 1),
            "self_consumption_ratio_percent": round(self_consumption_ratio, 1),
            "annual_savings_eur": round(annual_savings, 2),
            "payback_period_years": round(payback_years, 1),
            "battery_cycles": round(battery_cycles, 1),
            "total_investment_eur": round(total_investment, 2),
            # Neue Kennzahlen: Betriebsstunden und Volllaststunden
            "battery_charging_hours": battery_charging_hours,
            "battery_discharging_hours": battery_discharging_hours,
            "battery_operating_hours": battery_operating_hours,
            "battery_full_load_hours": round(battery_full_load_hours, 1),
            "battery_utilization_percent": round(battery_utilization_percent, 1),
            "battery_capacity_factor_percent": round(battery_capacity_factor_percent, 2),
            "pv_full_load_hours": round(pv_full_load_hours, 1),
        }
    
    def _generate_pv_output(
        self,
        pv_peak_kw: float,
        pv_tilt: float,
        hours: int
    ) -> np.ndarray:
        """
        Generate synthetic PV output profile
        
        Uses simplified model based on:
        - Day/night cycle
        - Seasonal variation
        - Germany-specific yield (~950 kWh/kWp/year)
        """
        output = np.zeros(hours)
        
        # Target annual yield: ~950 kWh per kWp for North Germany
        annual_yield_factor = 950  # kWh/kWp/year
        
        for hour in range(hours):
            day_of_year = hour // 24
            hour_of_day = hour % 24
            
            # Solar elevation approximation
            # Sunrise ~6-8am, sunset ~16-20pm depending on season
            summer_offset = np.sin(2 * np.pi * day_of_year / 365) * 2
            sunrise = 6 - summer_offset
            sunset = 18 + summer_offset
            
            if sunrise <= hour_of_day <= sunset:
                # Bell curve for daily production
                midday = (sunrise + sunset) / 2
                spread = (sunset - sunrise) / 4
                daily_factor = np.exp(-((hour_of_day - midday) ** 2) / (2 * spread ** 2))
                
                # Seasonal factor (higher in summer)
                seasonal_factor = 0.5 + 0.5 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
                
                # Weather factor (simplified: random reduction for clouds)
                np.random.seed(hour)  # Reproducible
                weather_factor = 0.6 + 0.4 * np.random.random()
                
                # Calculate hourly output
                output[hour] = pv_peak_kw * daily_factor * seasonal_factor * weather_factor
        
        # Scale to match expected annual yield
        actual_yield = output.sum() / pv_peak_kw
        if actual_yield > 0:
            output = output * (annual_yield_factor / actual_yield)
        
        return output
    
    def _generate_load_profile(
        self,
        annual_consumption_kwh: float,
        hours: int
    ) -> np.ndarray:
        """
        Generate commercial load profile
        
        Characteristics:
        - Higher during business hours (8-18)
        - Lower on weekends
        - Minimal at night
        """
        profile = np.zeros(hours)
        hourly_avg = annual_consumption_kwh / hours
        
        for hour in range(hours):
            day_of_year = hour // 24
            day_of_week = day_of_year % 7
            hour_of_day = hour % 24
            
            # Base load (10% always on)
            base_factor = 0.1
            
            # Time-of-day factor
            if 8 <= hour_of_day <= 18:
                time_factor = 1.0  # Business hours
            elif 6 <= hour_of_day < 8 or 18 < hour_of_day <= 22:
                time_factor = 0.4  # Shoulder hours
            else:
                time_factor = 0.15  # Night
            
            # Day-of-week factor
            if day_of_week < 5:  # Monday-Friday
                day_factor = 1.0
            elif day_of_week == 5:  # Saturday
                day_factor = 0.4
            else:  # Sunday
                day_factor = 0.2
            
            # Combine factors
            profile[hour] = hourly_avg * (base_factor + (1 - base_factor) * time_factor * day_factor)
        
        # Scale to match annual consumption
        actual_consumption = profile.sum()
        if actual_consumption > 0:
            profile = profile * (annual_consumption_kwh / actual_consumption)
        
        return profile
    
    def _simulate_battery(
        self,
        pv_output: np.ndarray,
        load_profile: np.ndarray,
        battery_kwh: float,
        battery_power_kw: float
    ) -> tuple:
        """
        Simulate battery charge/discharge behavior
        
        Strategy: Maximize self-consumption
        - Excess PV → charge battery
        - Deficit → discharge battery
        - Only use grid when necessary
        """
        hours = len(pv_output)
        
        battery_soc = np.zeros(hours)
        battery_charge = np.zeros(hours)
        battery_discharge = np.zeros(hours)
        grid_import = np.zeros(hours)
        grid_export = np.zeros(hours)
        
        # Battery parameters from centralized config
        soc_min_factor = SIMULATION_DEFAULTS.get("battery_soc_min", 0.10)
        soc_max_factor = SIMULATION_DEFAULTS.get("battery_soc_max", 0.90)
        roundtrip_efficiency = SIMULATION_DEFAULTS.get("battery_roundtrip_efficiency", 0.90)

        # Derive single-direction efficiency from round-trip (sqrt for symmetric)
        single_efficiency = roundtrip_efficiency ** 0.5  # ≈ 0.949 for 90% roundtrip

        min_soc = battery_kwh * soc_min_factor
        max_soc = battery_kwh * soc_max_factor
        current_soc = battery_kwh * 0.5  # Start at 50%
        charge_efficiency = single_efficiency
        discharge_efficiency = single_efficiency

        for hour in range(hours):
            pv = pv_output[hour]
            load = load_profile[hour]

            # Energy balance
            balance = pv - load  # Positive = surplus, Negative = deficit

            if balance > 0:
                # Surplus: Charge battery first, then export
                charge_possible = min(
                    balance,
                    battery_power_kw,
                    (max_soc - current_soc) / charge_efficiency
                )

                battery_charge[hour] = charge_possible
                current_soc += charge_possible * charge_efficiency
                grid_export[hour] = balance - charge_possible

            else:
                # Deficit: Discharge battery first, then import
                discharge_needed = -balance
                discharge_possible = min(
                    discharge_needed,
                    battery_power_kw,
                    (current_soc - min_soc) * discharge_efficiency
                )

                battery_discharge[hour] = discharge_possible
                current_soc -= discharge_possible / discharge_efficiency
                grid_import[hour] = discharge_needed - discharge_possible

            battery_soc[hour] = current_soc
        
        return (
            battery_soc,
            battery_charge,
            battery_discharge,
            grid_import,
            grid_export
        )
