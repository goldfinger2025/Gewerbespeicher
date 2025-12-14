"""
PVGIS Service
Direct integration with EU JRC PVGIS API for solar radiation and PV estimation
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import aiohttp
import pandas as pd
import numpy as np

from app.cache import RedisCache

logger = logging.getLogger(__name__)


# Cache expiration times
PVGIS_TMY_CACHE_DAYS = 30
PVGIS_HOURLY_CACHE_HOURS = 24
PVGIS_MONTHLY_CACHE_DAYS = 7


@dataclass
class IrradianceData:
    """Solar irradiance data for a location"""
    latitude: float
    longitude: float
    ghi_annual_kwh_m2: float  # Global Horizontal Irradiance
    dni_annual_kwh_m2: float  # Direct Normal Irradiance
    dhi_annual_kwh_m2: float  # Diffuse Horizontal Irradiance
    optimal_tilt: float  # Optimal panel tilt angle
    optimal_azimuth: float  # Optimal azimuth (typically 180 for N hemisphere)


@dataclass
class PVEstimation:
    """PV system estimation from PVGIS"""
    pv_peak_kw: float
    annual_production_kwh: float
    monthly_production_kwh: List[float]  # 12 values, Jan-Dec
    optimal_tilt: float
    optimal_azimuth: float
    system_loss_percent: float
    specific_yield_kwh_kwp: float  # kWh per kWp


@dataclass
class HourlyRadiation:
    """Hourly radiation data"""
    timestamps: List[datetime]
    ghi: List[float]  # W/m2
    dni: List[float]  # W/m2
    dhi: List[float]  # W/m2
    temperature: List[float]  # °C
    wind_speed: List[float]  # m/s


@dataclass
class MonthlyRadiation:
    """Monthly average radiation data"""
    month: int
    ghi_kwh_m2: float
    dni_kwh_m2: float
    dhi_kwh_m2: float
    avg_temperature: float
    sunshine_hours: float


class PVGISService:
    """
    PVGIS (Photovoltaic Geographical Information System) Service

    Provides access to EU JRC's PVGIS database for:
    - Solar radiation data
    - PV energy estimation
    - TMY (Typical Meteorological Year) data
    - Optimal system configuration

    API Documentation: https://re.jrc.ec.europa.eu/pvg_tools/en/

    Coverage:
    - Europe
    - Africa
    - Mediterranean Basin
    - Most of Asia (PVGIS-SARAH2 database)
    """

    # PVGIS API endpoints
    BASE_URL = "https://re.jrc.ec.europa.eu/api/v5_2"
    TMY_ENDPOINT = f"{BASE_URL}/tmy"
    PV_CALC_ENDPOINT = f"{BASE_URL}/PVcalc"
    SERIES_CALC_ENDPOINT = f"{BASE_URL}/seriescalc"
    MONTHLY_ENDPOINT = f"{BASE_URL}/MRcalc"

    # Default system parameters for Germany
    DEFAULT_TILT = 30  # degrees
    DEFAULT_AZIMUTH = 0  # 0 = South in PVGIS (different from pvlib!)
    DEFAULT_SYSTEM_LOSS = 14  # %

    # Radiation databases
    DATABASES = {
        "europe": "PVGIS-SARAH2",  # Satellite-based, covers Europe
        "africa": "PVGIS-SARAH2",
        "era5": "PVGIS-ERA5",  # Reanalysis data, global
    }

    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=60)

    def _get_cache_key(self, prefix: str, *args) -> str:
        """Generate cache key"""
        args_str = ":".join(str(round(a, 2) if isinstance(a, float) else a) for a in args)
        return f"pvgis:{prefix}:{args_str}"

    # ============ TMY DATA ============

    async def get_tmy_data(
        self,
        latitude: float,
        longitude: float,
        start_year: int = 2005,
        end_year: int = 2020
    ) -> Optional[pd.DataFrame]:
        """
        Get Typical Meteorological Year (TMY) data from PVGIS

        TMY data represents typical weather conditions based on historical data.
        Returns hourly values for 8760 hours (one year).

        Args:
            latitude: Location latitude (-65 to 65)
            longitude: Location longitude (-180 to 180)
            start_year: Start year for TMY calculation
            end_year: End year for TMY calculation

        Returns:
            DataFrame with hourly weather data (ghi, dni, dhi, temp_air, wind_speed)
        """
        cache_key = self._get_cache_key("tmy", latitude, longitude)

        # Check cache
        try:
            cached = await RedisCache.get_json(cache_key)
            if cached:
                df = pd.DataFrame(cached)
                logger.info(f"TMY data from cache: {latitude:.2f}, {longitude:.2f}")
                return df
        except Exception as e:
            logger.warning(f"Cache read error: {e}")

        # Fetch from PVGIS
        params = {
            "lat": latitude,
            "lon": longitude,
            "startyear": start_year,
            "endyear": end_year,
            "outputformat": "json",
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.TMY_ENDPOINT, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"PVGIS TMY error: {response.status} - {error_text}")
                        return None

                    data = await response.json()
                    hourly = data.get("outputs", {}).get("tmy_hourly", [])

                    if not hourly:
                        logger.warning("No TMY data returned")
                        return None

                    df = pd.DataFrame(hourly)

                    # Rename columns to standard names
                    column_map = {
                        "G(h)": "ghi",
                        "Gb(n)": "dni",
                        "Gd(h)": "dhi",
                        "T2m": "temp_air",
                        "WS10m": "wind_speed",
                        "RH": "relative_humidity",
                        "SP": "surface_pressure",
                    }
                    df = df.rename(columns=column_map)

                    # Cache result
                    try:
                        cache_data = df.to_dict(orient="list")
                        await RedisCache.set(
                            cache_key,
                            cache_data,
                            expire=PVGIS_TMY_CACHE_DAYS * 24 * 3600
                        )
                    except Exception as e:
                        logger.warning(f"Cache write error: {e}")

                    logger.info(f"TMY data fetched: {latitude:.2f}, {longitude:.2f}, {len(df)} hours")
                    return df

        except aiohttp.ClientError as e:
            logger.error(f"PVGIS connection error: {e}")
            return None
        except Exception as e:
            logger.error(f"PVGIS TMY error: {e}")
            return None

    # ============ PV ESTIMATION ============

    async def estimate_pv_production(
        self,
        latitude: float,
        longitude: float,
        pv_peak_kw: float,
        tilt: Optional[float] = None,
        azimuth: Optional[float] = None,
        system_loss: float = 14,
        mounting_type: str = "free"
    ) -> Optional[PVEstimation]:
        """
        Estimate annual PV production using PVGIS

        Args:
            latitude: Location latitude
            longitude: Location longitude
            pv_peak_kw: System peak power in kW
            tilt: Panel tilt angle (None = optimal)
            azimuth: Panel azimuth (0=South, -90=East, 90=West)
            system_loss: System losses in percent
            mounting_type: "free", "building", "vertical_axis", "inclined_axis", "2axis"

        Returns:
            PVEstimation with production estimates
        """
        cache_key = self._get_cache_key(
            "pvcalc", latitude, longitude, pv_peak_kw,
            tilt or "opt", azimuth or "opt", system_loss
        )

        # Check cache
        try:
            cached = await RedisCache.get_json(cache_key)
            if cached:
                return PVEstimation(**cached)
        except Exception:
            pass

        params = {
            "lat": latitude,
            "lon": longitude,
            "peakpower": pv_peak_kw,
            "loss": system_loss,
            "outputformat": "json",
        }

        # Mounting type
        mount_map = {
            "free": "free",
            "building": "building",
            "vertical_axis": "vertical_axis",
            "inclined_axis": "inclined_axis",
            "2axis": "two_axis",
        }
        params["mountingplace"] = mount_map.get(mounting_type, "free")

        # Optimal angle calculation if not specified
        if tilt is not None:
            params["angle"] = tilt
        else:
            params["optimalangles"] = 1

        if azimuth is not None:
            params["aspect"] = azimuth
        else:
            params["optimalangles"] = 1

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.PV_CALC_ENDPOINT, params=params) as response:
                    if response.status != 200:
                        logger.error(f"PVGIS PVcalc error: {response.status}")
                        return self._estimate_fallback(latitude, pv_peak_kw)

                    data = await response.json()
                    outputs = data.get("outputs", {})
                    inputs = data.get("inputs", {})

                    # Extract results
                    totals = outputs.get("totals", {}).get("fixed", {})
                    monthly = outputs.get("monthly", {}).get("fixed", [])

                    annual_kwh = totals.get("E_y", 0)
                    monthly_kwh = [m.get("E_m", 0) for m in monthly]

                    # Get optimal angles from inputs if used
                    mounting = inputs.get("mounting_system", {}).get("fixed", {})
                    opt_tilt = mounting.get("slope", {}).get("value", self.DEFAULT_TILT)
                    opt_azimuth = mounting.get("azimuth", {}).get("value", self.DEFAULT_AZIMUTH)

                    estimation = PVEstimation(
                        pv_peak_kw=pv_peak_kw,
                        annual_production_kwh=annual_kwh,
                        monthly_production_kwh=monthly_kwh,
                        optimal_tilt=opt_tilt,
                        optimal_azimuth=opt_azimuth,
                        system_loss_percent=system_loss,
                        specific_yield_kwh_kwp=annual_kwh / pv_peak_kw if pv_peak_kw > 0 else 0
                    )

                    # Cache result
                    try:
                        await RedisCache.set(
                            cache_key,
                            estimation.__dict__,
                            expire=PVGIS_MONTHLY_CACHE_DAYS * 24 * 3600
                        )
                    except Exception:
                        pass

                    logger.info(f"PV estimation: {pv_peak_kw} kWp -> {annual_kwh:.0f} kWh/year")
                    return estimation

        except Exception as e:
            logger.error(f"PVGIS PVcalc error: {e}")
            return self._estimate_fallback(latitude, pv_peak_kw)

    def _estimate_fallback(self, latitude: float, pv_peak_kw: float) -> PVEstimation:
        """Fallback PV estimation based on location"""
        # Specific yield in Germany: ~900-1100 kWh/kWp depending on location
        # North: ~900, South: ~1100
        lat_factor = (latitude - 47) / (55 - 47)  # 0=south, 1=north
        specific_yield = 1100 - (lat_factor * 200)

        annual_kwh = pv_peak_kw * specific_yield

        # Monthly distribution (typical German pattern)
        monthly_factors = [0.03, 0.05, 0.08, 0.10, 0.12, 0.13, 0.13, 0.12, 0.10, 0.07, 0.04, 0.03]
        monthly_kwh = [annual_kwh * f for f in monthly_factors]

        return PVEstimation(
            pv_peak_kw=pv_peak_kw,
            annual_production_kwh=annual_kwh,
            monthly_production_kwh=monthly_kwh,
            optimal_tilt=35 - (lat_factor * 5),  # 30-35° for Germany
            optimal_azimuth=0,  # South
            system_loss_percent=14,
            specific_yield_kwh_kwp=specific_yield
        )

    # ============ MONTHLY AVERAGES ============

    async def get_monthly_radiation(
        self,
        latitude: float,
        longitude: float
    ) -> List[MonthlyRadiation]:
        """
        Get monthly average radiation data

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            List of 12 MonthlyRadiation objects
        """
        cache_key = self._get_cache_key("monthly", latitude, longitude)

        # Check cache
        try:
            cached = await RedisCache.get_json(cache_key)
            if cached:
                return [MonthlyRadiation(**m) for m in cached]
        except Exception:
            pass

        # Fetch TMY and aggregate to monthly
        tmy_data = await self.get_tmy_data(latitude, longitude)

        if tmy_data is None:
            return self._generate_fallback_monthly(latitude)

        # Create datetime index
        tmy_data.index = pd.date_range(
            start="2024-01-01",
            periods=len(tmy_data),
            freq="h"
        )

        monthly_results = []

        for month in range(1, 13):
            mask = tmy_data.index.month == month
            month_data = tmy_data[mask]

            ghi_sum = month_data["ghi"].sum() / 1000 if "ghi" in month_data else 0
            dni_sum = month_data["dni"].sum() / 1000 if "dni" in month_data else 0
            dhi_sum = month_data["dhi"].sum() / 1000 if "dhi" in month_data else 0
            avg_temp = month_data["temp_air"].mean() if "temp_air" in month_data else 10

            # Estimate sunshine hours (GHI > 120 W/m2)
            sunshine_hours = len(month_data[month_data.get("ghi", 0) > 120])

            monthly_results.append(MonthlyRadiation(
                month=month,
                ghi_kwh_m2=round(ghi_sum, 1),
                dni_kwh_m2=round(dni_sum, 1),
                dhi_kwh_m2=round(dhi_sum, 1),
                avg_temperature=round(avg_temp, 1),
                sunshine_hours=sunshine_hours
            ))

        # Cache result
        try:
            await RedisCache.set(
                cache_key,
                [m.__dict__ for m in monthly_results],
                expire=PVGIS_MONTHLY_CACHE_DAYS * 24 * 3600
            )
        except Exception:
            pass

        return monthly_results

    def _generate_fallback_monthly(self, latitude: float) -> List[MonthlyRadiation]:
        """Generate fallback monthly data for Germany"""
        # Typical German values
        monthly_ghi = [25, 45, 80, 120, 155, 165, 165, 140, 95, 55, 30, 20]
        monthly_temp = [1, 2, 5, 9, 14, 17, 19, 19, 15, 10, 5, 2]
        monthly_sunshine = [45, 70, 120, 170, 220, 230, 230, 210, 160, 100, 55, 40]

        # Adjust for latitude
        lat_factor = (latitude - 47) / (55 - 47)  # 0=south, 1=north

        return [
            MonthlyRadiation(
                month=i + 1,
                ghi_kwh_m2=round(ghi * (1 - lat_factor * 0.1), 1),
                dni_kwh_m2=round(ghi * 0.5 * (1 - lat_factor * 0.1), 1),
                dhi_kwh_m2=round(ghi * 0.5, 1),
                avg_temperature=round(temp - lat_factor * 2, 1),
                sunshine_hours=round(hours * (1 - lat_factor * 0.1))
            )
            for i, (ghi, temp, hours) in enumerate(zip(monthly_ghi, monthly_temp, monthly_sunshine))
        ]

    # ============ IRRADIANCE DATA ============

    async def get_irradiance_summary(
        self,
        latitude: float,
        longitude: float
    ) -> IrradianceData:
        """
        Get annual irradiance summary for a location

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            IrradianceData with annual totals
        """
        monthly = await self.get_monthly_radiation(latitude, longitude)

        ghi_annual = sum(m.ghi_kwh_m2 for m in monthly)
        dni_annual = sum(m.dni_kwh_m2 for m in monthly)
        dhi_annual = sum(m.dhi_kwh_m2 for m in monthly)

        # Optimal tilt approximation: latitude - 10° to latitude
        optimal_tilt = max(20, min(45, latitude - 10))

        return IrradianceData(
            latitude=latitude,
            longitude=longitude,
            ghi_annual_kwh_m2=round(ghi_annual, 1),
            dni_annual_kwh_m2=round(dni_annual, 1),
            dhi_annual_kwh_m2=round(dhi_annual, 1),
            optimal_tilt=optimal_tilt,
            optimal_azimuth=180  # South (pvlib convention)
        )

    # ============ COMPARISON TOOLS ============

    async def compare_configurations(
        self,
        latitude: float,
        longitude: float,
        pv_peak_kw: float,
        configurations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Compare multiple PV configurations

        Args:
            latitude: Location latitude
            longitude: Location longitude
            pv_peak_kw: System peak power
            configurations: List of config dicts with 'tilt' and 'azimuth'

        Returns:
            List of results with production estimates
        """
        results = []

        for config in configurations:
            estimation = await self.estimate_pv_production(
                latitude=latitude,
                longitude=longitude,
                pv_peak_kw=pv_peak_kw,
                tilt=config.get("tilt"),
                azimuth=config.get("azimuth")
            )

            if estimation:
                results.append({
                    "configuration": config,
                    "annual_production_kwh": estimation.annual_production_kwh,
                    "specific_yield_kwh_kwp": estimation.specific_yield_kwh_kwp,
                    "monthly_production_kwh": estimation.monthly_production_kwh
                })

        return results

    async def get_optimal_configuration(
        self,
        latitude: float,
        longitude: float,
        pv_peak_kw: float
    ) -> Dict[str, Any]:
        """
        Get optimal PV configuration for a location

        Args:
            latitude: Location latitude
            longitude: Location longitude
            pv_peak_kw: System peak power

        Returns:
            Dict with optimal configuration and expected production
        """
        # Get estimation with optimal angles
        estimation = await self.estimate_pv_production(
            latitude=latitude,
            longitude=longitude,
            pv_peak_kw=pv_peak_kw,
            tilt=None,  # Let PVGIS calculate optimal
            azimuth=None
        )

        if not estimation:
            return {
                "error": "Could not calculate optimal configuration",
                "fallback_tilt": 30,
                "fallback_azimuth": 180
            }

        return {
            "optimal_tilt": estimation.optimal_tilt,
            "optimal_azimuth": estimation.optimal_azimuth,
            "annual_production_kwh": estimation.annual_production_kwh,
            "specific_yield_kwh_kwp": estimation.specific_yield_kwh_kwp,
            "monthly_production_kwh": estimation.monthly_production_kwh
        }


# Singleton instance
_pvgis_service: Optional[PVGISService] = None


def get_pvgis_service() -> PVGISService:
    """Get or create PVGIS service instance"""
    global _pvgis_service
    if _pvgis_service is None:
        _pvgis_service = PVGISService()
    return _pvgis_service
