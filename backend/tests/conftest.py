"""
Pytest Configuration and Shared Fixtures
=========================================

Shared fixtures for all calculation tests.
"""

import pytest
import numpy as np
from typing import Dict, Any


@pytest.fixture
def sample_simulation_params() -> Dict[str, Any]:
    """Standard simulation parameters for testing"""
    return {
        "pv_peak_kw": 30.0,
        "battery_kwh": 20.0,
        "battery_power_kw": 10.0,
        "annual_consumption_kwh": 50000.0,
        "electricity_price": 0.30,
        "feed_in_tariff": 0.0786,
        "pv_tilt": 30.0,
        "pv_azimuth": 180.0,
    }


@pytest.fixture
def sample_energy_flows() -> Dict[str, float]:
    """Sample energy flow values for KPI calculations"""
    return {
        "total_pv_generation": 28500.0,  # kWh/Jahr
        "total_load": 50000.0,  # kWh/Jahr
        "total_grid_import": 25000.0,  # kWh/Jahr
        "total_grid_export": 3500.0,  # kWh/Jahr
        "total_self_consumption": 25000.0,  # kWh/Jahr
        "total_battery_discharge": 8000.0,  # kWh/Jahr
    }


@pytest.fixture
def sample_financial_params() -> Dict[str, float]:
    """Standard financial parameters for testing"""
    return {
        "total_investment": 45000.0,  # EUR
        "annual_savings": 6000.0,  # EUR/Jahr
        "discount_rate": 0.03,  # 3%
        "project_lifetime": 20,  # Jahre
        "degradation_rate": 0.005,  # 0.5%/Jahr
    }


@pytest.fixture
def sample_load_profile() -> np.ndarray:
    """Generate a sample commercial load profile (8760 hours)"""
    hours = 8760
    profile = np.zeros(hours)
    hourly_avg = 50000 / hours  # 50 MWh/Jahr

    for hour in range(hours):
        day_of_week = (hour // 24) % 7
        hour_of_day = hour % 24

        # Basisverbrauch 10%
        base = 0.1

        # Geschäftszeiten 8-18 Uhr
        if 8 <= hour_of_day <= 18:
            time_factor = 1.0
        elif 6 <= hour_of_day < 8 or 18 < hour_of_day <= 22:
            time_factor = 0.4
        else:
            time_factor = 0.15

        # Wochenende reduziert
        if day_of_week < 5:
            day_factor = 1.0
        elif day_of_week == 5:
            day_factor = 0.4
        else:
            day_factor = 0.2

        profile[hour] = hourly_avg * (base + (1 - base) * time_factor * day_factor)

    # Skalieren auf Jahresverbrauch
    scale = 50000 / profile.sum()
    return profile * scale


@pytest.fixture
def sample_battery_params() -> Dict[str, float]:
    """Standard battery parameters from config"""
    return {
        "roundtrip_efficiency": 0.90,
        "soc_min": 0.10,
        "soc_max": 0.90,
        "cycle_life": 6000,
        "calendar_life_years": 15,
    }
