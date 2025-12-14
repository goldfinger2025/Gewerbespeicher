"""
Advanced PV + Storage Simulator using pvlib
Real PV calculations based on location, orientation, and weather data
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging
import aiohttp
import asyncio

# pvlib imports
import pvlib
from pvlib import pvsystem, modelchain, location
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS

logger = logging.getLogger(__name__)


class PVLibSimulator:
    """
    Advanced PV + Battery Storage Simulator using pvlib

    Features:
    - Real PV calculations with pvlib
    - PVGIS TMY weather data integration
    - Location-based irradiance modeling
    - Temperature-dependent efficiency
    - Multiple commercial load profiles
    """

    # Typical commercial load profile types
    LOAD_PROFILES = {
        "office": {
            "name": "Büro",
            "weekday_pattern": [0.1, 0.1, 0.1, 0.1, 0.1, 0.15, 0.3, 0.7, 0.9, 1.0, 1.0, 0.9, 0.8, 0.9, 1.0, 1.0, 0.9, 0.7, 0.4, 0.2, 0.15, 0.1, 0.1, 0.1],
            "saturday_factor": 0.3,
            "sunday_factor": 0.15,
        },
        "retail": {
            "name": "Einzelhandel",
            "weekday_pattern": [0.1, 0.1, 0.1, 0.1, 0.1, 0.15, 0.3, 0.5, 0.8, 0.9, 1.0, 1.0, 0.9, 0.9, 1.0, 1.0, 1.0, 0.9, 0.8, 0.6, 0.3, 0.15, 0.1, 0.1],
            "saturday_factor": 0.9,
            "sunday_factor": 0.4,
        },
        "production": {
            "name": "Produktion",
            "weekday_pattern": [0.3, 0.3, 0.3, 0.3, 0.3, 0.5, 0.9, 1.0, 1.0, 1.0, 1.0, 0.9, 0.8, 0.9, 1.0, 1.0, 1.0, 0.9, 0.7, 0.5, 0.4, 0.35, 0.3, 0.3],
            "saturday_factor": 0.6,
            "sunday_factor": 0.3,
        },
        "warehouse": {
            "name": "Lager/Logistik",
            "weekday_pattern": [0.2, 0.2, 0.2, 0.2, 0.2, 0.4, 0.7, 0.9, 1.0, 1.0, 1.0, 0.9, 0.8, 0.9, 1.0, 1.0, 0.9, 0.7, 0.5, 0.3, 0.25, 0.2, 0.2, 0.2],
            "saturday_factor": 0.5,
            "sunday_factor": 0.2,
        },
    }

    def __init__(self, latitude: float, longitude: float, altitude: float = 50):
        """
        Initialize simulator with location

        Args:
            latitude: Site latitude (e.g., 54.5 for North Germany)
            longitude: Site longitude (e.g., 9.3 for Handewitt)
            altitude: Site altitude in meters (default 50m)
        """
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude

        # Create pvlib location object
        self.location = location.Location(
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            tz='Europe/Berlin'
        )

        # Cache for weather data
        self._weather_cache: Optional[pd.DataFrame] = None

    async def get_pvgis_tmy_data(self) -> pd.DataFrame:
        """
        Fetch TMY (Typical Meteorological Year) data from PVGIS

        Returns hourly data for a typical year including:
        - GHI (Global Horizontal Irradiance)
        - DNI (Direct Normal Irradiance)
        - DHI (Diffuse Horizontal Irradiance)
        - Temperature
        - Wind speed
        """
        if self._weather_cache is not None:
            return self._weather_cache

        url = "https://re.jrc.ec.europa.eu/api/v5_2/tmy"
        params = {
            "lat": self.latitude,
            "lon": self.longitude,
            "outputformat": "json",
            "browser": 0,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Parse PVGIS response
                        hourly_data = data.get("outputs", {}).get("tmy_hourly", [])

                        if hourly_data:
                            df = pd.DataFrame(hourly_data)

                            # Create datetime index for a typical year
                            dates = pd.date_range(
                                start='2024-01-01',
                                periods=len(df),
                                freq='h',
                                tz='Europe/Berlin'
                            )
                            df.index = dates

                            # Rename columns to pvlib standard
                            column_map = {
                                'G(h)': 'ghi',
                                'Gb(n)': 'dni',
                                'Gd(h)': 'dhi',
                                'T2m': 'temp_air',
                                'WS10m': 'wind_speed',
                            }
                            df = df.rename(columns=column_map)

                            # Select only needed columns
                            available_cols = [c for c in ['ghi', 'dni', 'dhi', 'temp_air', 'wind_speed'] if c in df.columns]
                            df = df[available_cols]

                            self._weather_cache = df
                            logger.info(f"PVGIS TMY data loaded: {len(df)} hours")
                            return df

                    logger.warning(f"PVGIS request failed: {response.status}")

        except Exception as e:
            logger.warning(f"Failed to fetch PVGIS data: {e}")

        # Fallback to synthetic data
        logger.info("Using synthetic weather data")
        return self._generate_synthetic_weather()

    def _generate_synthetic_weather(self) -> pd.DataFrame:
        """Generate synthetic weather data as fallback"""
        dates = pd.date_range(
            start='2024-01-01',
            periods=8760,
            freq='h',
            tz='Europe/Berlin'
        )

        # Generate synthetic GHI based on location and time
        ghi = np.zeros(8760)
        dni = np.zeros(8760)
        dhi = np.zeros(8760)
        temp = np.zeros(8760)
        wind = np.zeros(8760)

        for i, dt in enumerate(dates):
            day_of_year = dt.dayofyear
            hour = dt.hour

            # Solar geometry approximation
            solar_noon = 12
            day_length = 8 + 8 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
            sunrise = solar_noon - day_length / 2
            sunset = solar_noon + day_length / 2

            if sunrise < hour < sunset:
                # Peak GHI around 1000 W/m² in summer, less in winter
                max_ghi = 600 + 400 * np.sin(2 * np.pi * (day_of_year - 80) / 365)

                # Bell curve for daily pattern
                solar_factor = np.sin(np.pi * (hour - sunrise) / (sunset - sunrise))

                ghi[i] = max_ghi * solar_factor
                dni[i] = ghi[i] * 0.7  # Approximate split
                dhi[i] = ghi[i] * 0.3

            # Temperature: 5-25°C range with seasonal variation
            temp[i] = 10 + 10 * np.sin(2 * np.pi * (day_of_year - 100) / 365) + 5 * np.sin(2 * np.pi * hour / 24)

            # Wind speed: 2-8 m/s
            wind[i] = 4 + 2 * np.random.random()

        return pd.DataFrame({
            'ghi': ghi,
            'dni': dni,
            'dhi': dhi,
            'temp_air': temp,
            'wind_speed': wind,
        }, index=dates)

    def create_pv_system(
        self,
        pv_peak_kw: float,
        tilt: float = 30,
        azimuth: float = 180,  # 180 = South
        module_type: str = "standard",
        inverter_efficiency: float = 0.96
    ) -> Tuple[pvsystem.PVSystem, modelchain.ModelChain]:
        """
        Create a PV system model

        Args:
            pv_peak_kw: System peak power in kW
            tilt: Panel tilt angle (0 = horizontal, 90 = vertical)
            azimuth: Panel azimuth (0 = North, 90 = East, 180 = South, 270 = West)
            module_type: Module type for temperature model
            inverter_efficiency: Inverter efficiency (0-1)

        Returns:
            Tuple of (PVSystem, ModelChain)
        """
        # Temperature model parameters
        temp_params = TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']

        # Create module parameters (generic monocrystalline)
        module_params = {
            'pdc0': pv_peak_kw * 1000,  # Watt
            'gamma_pdc': -0.004,  # Temperature coefficient (%/°C)
        }

        # Create inverter parameters
        inverter_params = {
            'pdc0': pv_peak_kw * 1000 * 1.1,  # Slightly oversized
            'eta_inv_nom': inverter_efficiency,
        }

        # Create mount
        mount = pvsystem.FixedMount(
            surface_tilt=tilt,
            surface_azimuth=azimuth
        )

        # Create array
        array = pvsystem.Array(
            mount=mount,
            module_parameters=module_params,
            temperature_model_parameters=temp_params,
        )

        # Create system
        system = pvsystem.PVSystem(
            arrays=[array],
            inverter_parameters=inverter_params,
        )

        # Create ModelChain
        mc = modelchain.ModelChain(
            system=system,
            location=self.location,
            aoi_model='physical',
            spectral_model='no_loss',
        )

        return system, mc

    def generate_load_profile(
        self,
        annual_consumption_kwh: float,
        profile_type: str = "office",
        year: int = 2024
    ) -> pd.Series:
        """
        Generate realistic commercial load profile

        Args:
            annual_consumption_kwh: Total annual consumption
            profile_type: Type of commercial building (office, retail, production, warehouse)
            year: Year for date index

        Returns:
            Hourly load profile as pandas Series
        """
        profile_config = self.LOAD_PROFILES.get(profile_type, self.LOAD_PROFILES["office"])

        dates = pd.date_range(
            start=f'{year}-01-01',
            periods=8760,
            freq='h',
            tz='Europe/Berlin'
        )

        load = np.zeros(8760)
        weekday_pattern = np.array(profile_config["weekday_pattern"])

        for i, dt in enumerate(dates):
            hour = dt.hour
            day_of_week = dt.dayofweek  # 0 = Monday

            # Get base pattern value
            base_load = weekday_pattern[hour]

            # Apply day factor
            if day_of_week < 5:  # Monday - Friday
                day_factor = 1.0
            elif day_of_week == 5:  # Saturday
                day_factor = profile_config["saturday_factor"]
            else:  # Sunday
                day_factor = profile_config["sunday_factor"]

            # Seasonal variation (higher in winter for heating/lighting)
            day_of_year = dt.dayofyear
            seasonal_factor = 1.0 + 0.15 * np.cos(2 * np.pi * (day_of_year - 172) / 365)

            load[i] = base_load * day_factor * seasonal_factor

        # Scale to match annual consumption
        load_series = pd.Series(load, index=dates)
        current_total = load_series.sum()
        if current_total > 0:
            load_series = load_series * (annual_consumption_kwh / current_total)

        return load_series

    async def simulate_year(
        self,
        pv_peak_kw: float,
        battery_kwh: float,
        battery_power_kw: float,
        annual_consumption_kwh: float,
        electricity_price: float = 0.30,
        feed_in_tariff: float = 0.08,
        pv_tilt: float = 30.0,
        pv_azimuth: float = 180.0,
        load_profile_type: str = "office",
        year: int = 2024
    ) -> Dict:
        """
        Run full year simulation with hourly resolution using pvlib

        Args:
            pv_peak_kw: PV system peak power in kW
            battery_kwh: Battery capacity in kWh
            battery_power_kw: Battery max charge/discharge power in kW
            annual_consumption_kwh: Annual electricity consumption in kWh
            electricity_price: Electricity price in €/kWh
            feed_in_tariff: Feed-in tariff in €/kWh
            pv_tilt: PV panel tilt angle in degrees
            pv_azimuth: PV panel azimuth (180 = South)
            load_profile_type: Type of commercial building
            year: Simulation year

        Returns:
            Dict with detailed simulation results
        """
        logger.info(f"Starting pvlib simulation: {pv_peak_kw} kWp, {battery_kwh} kWh battery")

        # ============ 1. GET WEATHER DATA ============
        weather = await self.get_pvgis_tmy_data()

        # ============ 2. CALCULATE PV OUTPUT ============
        system, mc = self.create_pv_system(
            pv_peak_kw=pv_peak_kw,
            tilt=pv_tilt,
            azimuth=pv_azimuth
        )

        try:
            # Run modelchain
            mc.run_model(weather)
            pv_output = mc.results.ac / 1000  # Convert W to kW
            pv_output = pv_output.clip(lower=0)  # No negative values
        except Exception as e:
            logger.warning(f"pvlib modelchain failed: {e}, using fallback")
            pv_output = self._fallback_pv_output(pv_peak_kw, weather)

        # ============ 3. GENERATE LOAD PROFILE ============
        load_profile = self.generate_load_profile(
            annual_consumption_kwh=annual_consumption_kwh,
            profile_type=load_profile_type,
            year=year
        )

        # Align indices
        pv_output = pv_output.reindex(load_profile.index, fill_value=0)

        # ============ 4. SIMULATE BATTERY ============
        (
            battery_soc,
            battery_charge,
            battery_discharge,
            grid_import,
            grid_export,
            self_consumption
        ) = self._simulate_battery(
            pv_output=pv_output.values,
            load_profile=load_profile.values,
            battery_kwh=battery_kwh,
            battery_power_kw=battery_power_kw
        )

        # ============ 5. CALCULATE KPIs ============
        total_pv_generation = float(pv_output.sum())
        total_load = float(load_profile.sum())
        total_grid_import = float(grid_import.sum())
        total_grid_export = float(grid_export.sum())
        total_self_consumption = float(self_consumption.sum())
        total_battery_discharge = float(battery_discharge.sum())

        # Autarkiegrad
        autonomy_degree = 0
        if total_load > 0:
            autonomy_degree = ((total_load - total_grid_import) / total_load) * 100
            autonomy_degree = max(0, min(100, autonomy_degree))

        # Eigenverbrauchsquote
        self_consumption_ratio = 0
        if total_pv_generation > 0:
            self_consumption_ratio = (total_self_consumption / total_pv_generation) * 100

        # PV coverage
        pv_coverage = 0
        if total_load > 0:
            pv_coverage = (total_pv_generation / total_load) * 100

        # Battery cycles
        battery_cycles = total_battery_discharge / battery_kwh if battery_kwh > 0 else 0

        # ============ 6. FINANCIAL CALCULATIONS ============
        # Costs without system
        cost_without_system = total_load * electricity_price

        # Costs with system
        cost_grid_import = total_grid_import * electricity_price
        revenue_feed_in = total_grid_export * feed_in_tariff
        cost_with_system = cost_grid_import - revenue_feed_in

        # Annual savings
        annual_savings = cost_without_system - cost_with_system

        # Investment costs (realistic German prices 2024)
        pv_cost_per_kwp = 1100  # €/kWp including installation
        battery_cost_per_kwh = 600  # €/kWh including BMS
        fixed_costs = 2000  # Planning, permits, etc.

        pv_cost = pv_peak_kw * pv_cost_per_kwp
        battery_cost = battery_kwh * battery_cost_per_kwh
        total_investment = pv_cost + battery_cost + fixed_costs

        # Payback period
        payback_years = total_investment / annual_savings if annual_savings > 0 else 99

        # NPV calculation (20 years, 3% discount rate)
        discount_rate = 0.03
        project_lifetime = 20
        npv = -total_investment
        for year_i in range(1, project_lifetime + 1):
            # Assume 0.5% degradation per year
            degradation_factor = (1 - 0.005) ** year_i
            yearly_savings = annual_savings * degradation_factor
            npv += yearly_savings / ((1 + discount_rate) ** year_i)

        # IRR approximation
        irr = (annual_savings / total_investment) * 100 if total_investment > 0 else 0

        # Total savings over lifetime
        total_savings_lifetime = annual_savings * project_lifetime * 0.95  # Account for degradation

        # ============ 7. MONTHLY SUMMARY ============
        monthly_summary = self._calculate_monthly_summary(
            pv_output, load_profile, grid_import, grid_export, self_consumption
        )

        logger.info(f"Simulation complete: {autonomy_degree:.1f}% autonomy, {annual_savings:.0f}€ savings")

        return {
            # Energy KPIs
            "pv_generation_kwh": round(total_pv_generation, 2),
            "self_consumption_kwh": round(total_self_consumption, 2),
            "grid_import_kwh": round(total_grid_import, 2),
            "grid_export_kwh": round(total_grid_export, 2),
            "total_consumption_kwh": round(total_load, 2),

            # Percentages
            "autonomy_degree_percent": round(autonomy_degree, 1),
            "self_consumption_ratio_percent": round(self_consumption_ratio, 1),
            "pv_coverage_percent": round(pv_coverage, 1),

            # Battery
            "battery_cycles": round(battery_cycles, 1),
            "battery_throughput_kwh": round(total_battery_discharge, 2),

            # Financial
            "annual_savings_eur": round(annual_savings, 2),
            "total_savings_eur": round(total_savings_lifetime, 2),
            "payback_period_years": round(min(payback_years, 99), 1),
            "npv_eur": round(npv, 2),
            "irr_percent": round(irr, 1),
            "total_investment_eur": round(total_investment, 2),

            # Costs breakdown
            "cost_without_system_eur": round(cost_without_system, 2),
            "cost_with_system_eur": round(cost_with_system, 2),
            "grid_cost_eur": round(cost_grid_import, 2),
            "feed_in_revenue_eur": round(revenue_feed_in, 2),

            # Monthly data
            "monthly_summary": monthly_summary,

            # Metadata
            "simulation_type": "pvlib",
            "location": {
                "latitude": self.latitude,
                "longitude": self.longitude,
            },
            "system_config": {
                "pv_peak_kw": pv_peak_kw,
                "battery_kwh": battery_kwh,
                "tilt": pv_tilt,
                "azimuth": pv_azimuth,
                "load_profile_type": load_profile_type,
            }
        }

    def _fallback_pv_output(self, pv_peak_kw: float, weather: pd.DataFrame) -> pd.Series:
        """Fallback PV calculation if modelchain fails"""
        # Simple calculation: GHI * system efficiency * peak power
        system_efficiency = 0.15  # Typical panel efficiency
        performance_ratio = 0.85  # System losses

        if 'ghi' in weather.columns:
            pv_power = weather['ghi'] * system_efficiency * performance_ratio * pv_peak_kw / 1000
        else:
            pv_power = pd.Series(0, index=weather.index)

        return pv_power.clip(lower=0, upper=pv_peak_kw)

    def _simulate_battery(
        self,
        pv_output: np.ndarray,
        load_profile: np.ndarray,
        battery_kwh: float,
        battery_power_kw: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Simulate battery operation with self-consumption optimization

        Returns:
            Tuple of (soc, charge, discharge, grid_import, grid_export, self_consumption)
        """
        hours = len(pv_output)

        battery_soc = np.zeros(hours)
        battery_charge = np.zeros(hours)
        battery_discharge = np.zeros(hours)
        grid_import = np.zeros(hours)
        grid_export = np.zeros(hours)
        self_consumption = np.zeros(hours)

        # Battery parameters
        current_soc = battery_kwh * 0.5  # Start at 50%
        min_soc = battery_kwh * 0.1  # 10% minimum
        max_soc = battery_kwh * 0.9  # 90% maximum
        charge_efficiency = 0.95
        discharge_efficiency = 0.95

        for hour in range(hours):
            pv = pv_output[hour]
            load = load_profile[hour]

            # Direct self-consumption
            direct_consumption = min(pv, load)
            self_consumption[hour] = direct_consumption

            surplus = pv - direct_consumption
            deficit = load - direct_consumption

            if surplus > 0:
                # Excess PV: charge battery, then export
                charge_possible = min(
                    surplus,
                    battery_power_kw,
                    (max_soc - current_soc) / charge_efficiency
                )

                battery_charge[hour] = charge_possible
                current_soc += charge_possible * charge_efficiency
                grid_export[hour] = surplus - charge_possible

            elif deficit > 0:
                # Deficit: discharge battery, then import
                discharge_possible = min(
                    deficit,
                    battery_power_kw,
                    (current_soc - min_soc) * discharge_efficiency
                )

                battery_discharge[hour] = discharge_possible
                current_soc -= discharge_possible / discharge_efficiency
                grid_import[hour] = deficit - discharge_possible

                # Add battery discharge to self-consumption
                self_consumption[hour] += discharge_possible

            battery_soc[hour] = current_soc

        return (
            battery_soc,
            battery_charge,
            battery_discharge,
            grid_import,
            grid_export,
            self_consumption
        )

    def _calculate_monthly_summary(
        self,
        pv_output: pd.Series,
        load_profile: pd.Series,
        grid_import: np.ndarray,
        grid_export: np.ndarray,
        self_consumption: np.ndarray
    ) -> list:
        """Calculate monthly summary statistics"""
        # Convert arrays to Series with same index
        grid_import_series = pd.Series(grid_import, index=pv_output.index)
        grid_export_series = pd.Series(grid_export, index=pv_output.index)
        self_consumption_series = pd.Series(self_consumption, index=pv_output.index)

        monthly_data = []

        for month in range(1, 13):
            mask = pv_output.index.month == month

            pv_month = float(pv_output[mask].sum())
            load_month = float(load_profile[mask].sum())
            import_month = float(grid_import_series[mask].sum())
            export_month = float(grid_export_series[mask].sum())
            self_cons_month = float(self_consumption_series[mask].sum())

            # Calculate monthly autonomy
            autonomy_month = 0
            if load_month > 0:
                autonomy_month = ((load_month - import_month) / load_month) * 100

            monthly_data.append({
                "month": month,
                "pv_generation_kwh": round(pv_month, 1),
                "consumption_kwh": round(load_month, 1),
                "self_consumption_kwh": round(self_cons_month, 1),
                "grid_import_kwh": round(import_month, 1),
                "grid_export_kwh": round(export_month, 1),
                "autonomy_percent": round(autonomy_month, 1),
            })

        return monthly_data


# Factory function for backward compatibility
def get_simulator(latitude: float, longitude: float, use_pvlib: bool = True) -> PVLibSimulator:
    """
    Get simulator instance

    Args:
        latitude: Site latitude
        longitude: Site longitude
        use_pvlib: Whether to use pvlib (always True now)

    Returns:
        PVLibSimulator instance
    """
    return PVLibSimulator(latitude=latitude, longitude=longitude)
