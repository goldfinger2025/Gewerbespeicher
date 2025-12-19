"""
Advanced PV + Storage Simulator using pvlib
Real PV calculations based on location, orientation, and weather data
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
import logging
import aiohttp

# pvlib imports
from pvlib import pvsystem, modelchain, location
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS

from app.cache import RedisCache
from app.config import INVESTMENT_COSTS_2025, SIMULATION_DEFAULTS

logger = logging.getLogger(__name__)


# Cache expiration time for PVGIS data (30 days in seconds)
PVGIS_CACHE_EXPIRATION = 30 * 24 * 60 * 60  # 30 days


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

    def _get_pvgis_cache_key(self) -> str:
        """Generate cache key for PVGIS data based on location"""
        # Round coordinates to 2 decimal places for cache efficiency
        # (covers ~1km precision which is sufficient for TMY data)
        lat_rounded = round(self.latitude, 2)
        lon_rounded = round(self.longitude, 2)
        key_string = f"pvgis:tmy:{lat_rounded}:{lon_rounded}"
        return key_string

    async def get_pvgis_tmy_data(self) -> pd.DataFrame:
        """
        Fetch TMY (Typical Meteorological Year) data from PVGIS with Redis caching

        Returns hourly data for a typical year including:
        - GHI (Global Horizontal Irradiance)
        - DNI (Direct Normal Irradiance)
        - DHI (Diffuse Horizontal Irradiance)
        - Temperature
        - Wind speed

        Data is cached in Redis for 30 days to reduce API calls.
        """
        # Check in-memory cache first
        if self._weather_cache is not None:
            return self._weather_cache

        cache_key = self._get_pvgis_cache_key()

        # Try to get from Redis cache
        try:
            cached_data = await RedisCache.get_json(cache_key)
            if cached_data is not None:
                logger.info(f"PVGIS data loaded from Redis cache: {cache_key}")
                df = pd.DataFrame(cached_data)
                # Recreate datetime index
                dates = pd.date_range(
                    start='2024-01-01',
                    periods=len(df),
                    freq='h',
                    tz='Europe/Berlin'
                )
                df.index = dates
                self._weather_cache = df
                return df
        except Exception as e:
            logger.warning(f"Redis cache read failed: {e}")

        # Fetch from PVGIS API
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

                            # Store in Redis cache (without index for JSON serialization)
                            try:
                                cache_data = df.reset_index(drop=True).to_dict(orient='list')
                                await RedisCache.set(
                                    cache_key,
                                    cache_data,
                                    expire=PVGIS_CACHE_EXPIRATION
                                )
                                logger.info(f"PVGIS data cached in Redis: {cache_key}")
                            except Exception as e:
                                logger.warning(f"Failed to cache PVGIS data: {e}")

                            self._weather_cache = df
                            logger.info(f"PVGIS TMY data loaded from API: {len(df)} hours")
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
            self_consumption,
            battery_charging_hours,
            battery_discharging_hours,
            battery_operating_hours
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

        # ============ VOLLLASTSTUNDEN (Full Load Hours) ============
        # PV-Volllaststunden: Stunden bei Nennleistung für gleiche Energiemenge
        pv_full_load_hours = total_pv_generation / pv_peak_kw if pv_peak_kw > 0 else 0

        # Batterie-Volllaststunden (Entladung): Entladeenergie / Nennleistung
        battery_full_load_hours = total_battery_discharge / battery_power_kw if battery_power_kw > 0 else 0

        # Batterie-Nutzungsgrad: Betriebsstunden / Gesamtstunden Jahr (8760h)
        battery_utilization_percent = (battery_operating_hours / 8760) * 100 if battery_operating_hours > 0 else 0

        # ============ 6. FINANCIAL CALCULATIONS ============
        # Costs without system
        cost_without_system = total_load * electricity_price

        # Costs with system
        cost_grid_import = total_grid_import * electricity_price
        revenue_feed_in = total_grid_export * feed_in_tariff
        cost_with_system = cost_grid_import - revenue_feed_in

        # Annual savings
        annual_savings = cost_without_system - cost_with_system

        # Investment costs from centralized config (Stand: Dezember 2025)
        # Use size-dependent pricing from INVESTMENT_COSTS_2025
        if pv_peak_kw <= 30:
            pv_cost_per_kwp = INVESTMENT_COSTS_2025["pv_cost_per_kwp"]["bis_30kwp"]
        elif pv_peak_kw <= 100:
            pv_cost_per_kwp = INVESTMENT_COSTS_2025["pv_cost_per_kwp"]["30_100kwp"]
        elif pv_peak_kw <= 500:
            pv_cost_per_kwp = INVESTMENT_COSTS_2025["pv_cost_per_kwp"]["100_500kwp"]
        else:
            pv_cost_per_kwp = INVESTMENT_COSTS_2025["pv_cost_per_kwp"]["ueber_500kwp"]

        if battery_kwh <= 30:
            battery_cost_per_kwh = INVESTMENT_COSTS_2025["battery_cost_per_kwh"]["bis_30kwh"]
        elif battery_kwh <= 100:
            battery_cost_per_kwh = INVESTMENT_COSTS_2025["battery_cost_per_kwh"]["30_100kwh"]
        elif battery_kwh <= 500:
            battery_cost_per_kwh = INVESTMENT_COSTS_2025["battery_cost_per_kwh"]["100_500kwh"]
        else:
            battery_cost_per_kwh = INVESTMENT_COSTS_2025["battery_cost_per_kwh"]["ueber_500kwh"]

        fixed_costs = sum(INVESTMENT_COSTS_2025["fixed_costs"].values())

        pv_cost = pv_peak_kw * pv_cost_per_kwp
        battery_cost = battery_kwh * battery_cost_per_kwh
        total_investment = pv_cost + battery_cost + fixed_costs

        # Simple payback period (branchenüblich)
        payback_years = total_investment / annual_savings if annual_savings > 0 else 99

        # Discounted payback period (finanziell präziser)
        # Findet das Jahr, in dem kumulierte abgezinste Cashflows die Investition übersteigen
        def calculate_discounted_payback(investment: float, annual_cf: float,
                                         discount_rate: float, years: int,
                                         degradation: float = 0.005) -> float:
            if investment <= 0 or annual_cf <= 0:
                return 99.0

            cumulative_dcf = 0.0
            for year in range(1, years + 1):
                cf = annual_cf * ((1 - degradation) ** year)
                dcf = cf / ((1 + discount_rate) ** year)
                cumulative_dcf += dcf

                if cumulative_dcf >= investment:
                    # Interpolation für genaueren Wert
                    previous_cumulative = cumulative_dcf - dcf
                    remaining = investment - previous_cumulative
                    fraction = remaining / dcf if dcf > 0 else 0
                    return year - 1 + fraction

            return 99.0  # Nicht innerhalb der Projektlaufzeit amortisiert

        # NPV calculation using centralized parameters
        discount_rate = SIMULATION_DEFAULTS["discount_rate"]
        project_lifetime = SIMULATION_DEFAULTS["project_lifetime_years"]
        degradation_rate = SIMULATION_DEFAULTS["pv_degradation_jahr"]

        npv = -total_investment
        for year_i in range(1, project_lifetime + 1):
            degradation_factor = (1 - degradation_rate) ** year_i
            yearly_savings = annual_savings * degradation_factor
            npv += yearly_savings / ((1 + discount_rate) ** year_i)

        # IRR calculation using Newton-Raphson approximation
        # IRR is the discount rate where NPV = 0
        # Simplified IRR approximation based on cash flows
        def calculate_irr(investment: float, annual_cf: float, years: int, degradation: float = 0.005) -> float:
            """Calculate IRR using iterative Newton-Raphson method"""
            if investment <= 0 or annual_cf <= 0:
                return 0.0

            # Initial guess based on simple payback
            rate = annual_cf / investment

            for _ in range(50):  # Max iterations
                npv_val = -investment
                npv_derivative = 0

                for year in range(1, years + 1):
                    cf = annual_cf * ((1 - degradation) ** year)
                    discount = (1 + rate) ** year
                    npv_val += cf / discount
                    npv_derivative -= year * cf / ((1 + rate) ** (year + 1))

                if abs(npv_derivative) < 1e-10:
                    break

                rate_new = rate - npv_val / npv_derivative

                if abs(rate_new - rate) < 1e-6:
                    break

                rate = max(0.001, min(0.5, rate_new))  # Clamp between 0.1% and 50%

            return rate * 100  # Return as percentage

        irr = calculate_irr(total_investment, annual_savings, project_lifetime, degradation_rate)

        # Discounted payback calculation
        discounted_payback = calculate_discounted_payback(
            total_investment, annual_savings, discount_rate, project_lifetime, degradation_rate
        )

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
            "battery_charging_hours": battery_charging_hours,
            "battery_discharging_hours": battery_discharging_hours,
            "battery_operating_hours": battery_operating_hours,
            "battery_full_load_hours": round(battery_full_load_hours, 1),
            "battery_utilization_percent": round(battery_utilization_percent, 1),

            # PV
            "pv_full_load_hours": round(pv_full_load_hours, 1),

            # Financial
            "annual_savings_eur": round(annual_savings, 2),
            "total_savings_eur": round(total_savings_lifetime, 2),
            "payback_period_years": round(min(payback_years, 99), 1),
            "discounted_payback_years": round(min(discounted_payback, 99), 1),
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
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, int, int]:
        """
        Simulate battery operation with self-consumption optimization

        Returns:
            Tuple of (soc, charge, discharge, grid_import, grid_export, self_consumption,
                      charging_hours, discharging_hours, operating_hours)
        """
        hours = len(pv_output)

        battery_soc = np.zeros(hours)
        battery_charge = np.zeros(hours)
        battery_discharge = np.zeros(hours)
        grid_import = np.zeros(hours)
        grid_export = np.zeros(hours)
        self_consumption = np.zeros(hours)

        # Battery parameters from centralized config
        # SOC limits from config (default: 10% min, 90% max)
        soc_min_factor = SIMULATION_DEFAULTS.get("battery_soc_min", 0.10)
        soc_max_factor = SIMULATION_DEFAULTS.get("battery_soc_max", 0.90)
        roundtrip_efficiency = SIMULATION_DEFAULTS.get("battery_roundtrip_efficiency", 0.90)

        # Derive single-direction efficiency from round-trip (sqrt for symmetric)
        # Round-trip = charge_eff * discharge_eff, assuming equal: each = sqrt(roundtrip)
        single_efficiency = roundtrip_efficiency ** 0.5  # ≈ 0.949 for 90% roundtrip

        current_soc = battery_kwh * 0.5  # Start at 50%
        min_soc = battery_kwh * soc_min_factor
        max_soc = battery_kwh * soc_max_factor
        charge_efficiency = single_efficiency
        discharge_efficiency = single_efficiency

        # Betriebsstunden-Zähler
        charging_hours = 0
        discharging_hours = 0

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

                # Zähle Ladestunde wenn tatsächlich geladen wurde
                if charge_possible > 0:
                    charging_hours += 1

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

                # Zähle Entladestunde wenn tatsächlich entladen wurde
                if discharge_possible > 0:
                    discharging_hours += 1

            battery_soc[hour] = current_soc

        # Gesamte Betriebsstunden (Laden ODER Entladen)
        operating_hours = charging_hours + discharging_hours

        return (
            battery_soc,
            battery_charge,
            battery_discharge,
            grid_import,
            grid_export,
            self_consumption,
            charging_hours,
            discharging_hours,
            operating_hours
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
