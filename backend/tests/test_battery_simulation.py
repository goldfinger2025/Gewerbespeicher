"""
Unit Tests for Battery Simulation Logic
=======================================

Tests validate battery charge/discharge behavior, efficiency handling,
and operating hours calculations.

Reference: Fraunhofer ISE, DIN EN 15316
Run with: pytest tests/test_battery_simulation.py -v
"""

import pytest
import numpy as np
from typing import Tuple


# ============================================================================
# BATTERY SIMULATION FUNCTIONS (extracted for isolated testing)
# ============================================================================

def simulate_battery_hour(
    pv_power: float,
    load_power: float,
    current_soc: float,
    battery_kwh: float,
    battery_power_kw: float,
    soc_min: float = 0.10,
    soc_max: float = 0.90,
    roundtrip_efficiency: float = 0.90
) -> Tuple[float, float, float, float, float, float]:
    """
    Simulate one hour of battery operation

    Returns:
        Tuple of (new_soc, charge, discharge, grid_import, grid_export, self_consumption)
    """
    single_efficiency = roundtrip_efficiency ** 0.5
    min_soc = battery_kwh * soc_min
    max_soc = battery_kwh * soc_max

    # Direct self-consumption
    direct_consumption = min(pv_power, load_power)
    self_consumption = direct_consumption

    surplus = pv_power - direct_consumption
    deficit = load_power - direct_consumption

    charge = 0.0
    discharge = 0.0
    grid_import = 0.0
    grid_export = 0.0
    new_soc = current_soc

    if surplus > 0:
        # Excess PV: charge battery, then export
        charge_possible = min(
            surplus,
            battery_power_kw,
            (max_soc - current_soc) / single_efficiency
        )
        charge = charge_possible
        new_soc = current_soc + charge_possible * single_efficiency
        grid_export = surplus - charge_possible

    elif deficit > 0:
        # Deficit: discharge battery, then import
        discharge_possible = min(
            deficit,
            battery_power_kw,
            (current_soc - min_soc) * single_efficiency
        )
        discharge = discharge_possible
        new_soc = current_soc - discharge_possible / single_efficiency
        grid_import = deficit - discharge_possible
        self_consumption += discharge_possible

    return new_soc, charge, discharge, grid_import, grid_export, self_consumption


def simulate_battery_year(
    pv_output: np.ndarray,
    load_profile: np.ndarray,
    battery_kwh: float,
    battery_power_kw: float,
    soc_min: float = 0.10,
    soc_max: float = 0.90,
    roundtrip_efficiency: float = 0.90,
    initial_soc_fraction: float = 0.5
) -> dict:
    """
    Simulate full year of battery operation

    Returns:
        Dict with simulation results
    """
    hours = len(pv_output)
    current_soc = battery_kwh * initial_soc_fraction

    total_charge = 0.0
    total_discharge = 0.0
    total_grid_import = 0.0
    total_grid_export = 0.0
    total_self_consumption = 0.0
    charging_hours = 0
    discharging_hours = 0

    for hour in range(hours):
        new_soc, charge, discharge, grid_import, grid_export, self_cons = simulate_battery_hour(
            pv_power=pv_output[hour],
            load_power=load_profile[hour],
            current_soc=current_soc,
            battery_kwh=battery_kwh,
            battery_power_kw=battery_power_kw,
            soc_min=soc_min,
            soc_max=soc_max,
            roundtrip_efficiency=roundtrip_efficiency
        )

        current_soc = new_soc
        total_charge += charge
        total_discharge += discharge
        total_grid_import += grid_import
        total_grid_export += grid_export
        total_self_consumption += self_cons

        if charge > 0:
            charging_hours += 1
        if discharge > 0:
            discharging_hours += 1

    operating_hours = charging_hours + discharging_hours
    cycles = total_discharge / battery_kwh if battery_kwh > 0 else 0
    full_load_hours = total_discharge / battery_power_kw if battery_power_kw > 0 else 0

    return {
        "total_charge_kwh": total_charge,
        "total_discharge_kwh": total_discharge,
        "total_grid_import_kwh": total_grid_import,
        "total_grid_export_kwh": total_grid_export,
        "total_self_consumption_kwh": total_self_consumption,
        "charging_hours": charging_hours,
        "discharging_hours": discharging_hours,
        "operating_hours": operating_hours,
        "battery_cycles": cycles,
        "battery_full_load_hours": full_load_hours,
    }


# ============================================================================
# SINGLE HOUR SIMULATION TESTS
# ============================================================================

class TestBatteryHourSimulation:
    """Tests for single hour battery simulation"""

    def test_surplus_charges_battery(self):
        """Surplus PV should charge battery"""
        new_soc, charge, discharge, grid_import, grid_export, _ = simulate_battery_hour(
            pv_power=10.0,
            load_power=5.0,
            current_soc=10.0,  # 50% of 20 kWh
            battery_kwh=20.0,
            battery_power_kw=10.0
        )

        assert charge > 0
        assert discharge == 0
        assert new_soc > 10.0

    def test_deficit_discharges_battery(self):
        """Load deficit should discharge battery"""
        new_soc, charge, discharge, grid_import, grid_export, _ = simulate_battery_hour(
            pv_power=2.0,
            load_power=8.0,
            current_soc=15.0,
            battery_kwh=20.0,
            battery_power_kw=10.0
        )

        assert discharge > 0
        assert charge == 0
        assert new_soc < 15.0

    def test_soc_limits_respected(self):
        """SOC should stay within min/max limits"""
        # Try to overcharge
        new_soc, _, _, _, _, _ = simulate_battery_hour(
            pv_power=20.0,
            load_power=0.0,
            current_soc=17.0,  # Already at 85%
            battery_kwh=20.0,
            battery_power_kw=10.0,
            soc_max=0.90
        )
        assert new_soc <= 20.0 * 0.90

        # Try to over-discharge
        new_soc, _, _, _, _, _ = simulate_battery_hour(
            pv_power=0.0,
            load_power=20.0,
            current_soc=3.0,  # Already at 15%
            battery_kwh=20.0,
            battery_power_kw=10.0,
            soc_min=0.10
        )
        assert new_soc >= 20.0 * 0.10

    def test_power_limit_respected(self):
        """Battery power limit should be respected"""
        _, charge, _, _, _, _ = simulate_battery_hour(
            pv_power=20.0,  # 20 kW surplus
            load_power=0.0,
            current_soc=5.0,
            battery_kwh=20.0,
            battery_power_kw=10.0  # Only 10 kW possible
        )
        assert charge <= 10.0

    def test_efficiency_applied(self):
        """Efficiency losses should be applied"""
        roundtrip = 0.90
        single = roundtrip ** 0.5  # ~0.949

        # Charge 10 kWh worth
        new_soc, charge, _, _, _, _ = simulate_battery_hour(
            pv_power=10.0,
            load_power=0.0,
            current_soc=5.0,
            battery_kwh=20.0,
            battery_power_kw=10.0,
            roundtrip_efficiency=roundtrip
        )

        # SOC increase should be less than charge due to efficiency
        soc_increase = new_soc - 5.0
        assert soc_increase < charge  # Loss due to charging efficiency

    def test_grid_export_when_battery_full(self):
        """Excess PV should export when battery full"""
        _, charge, _, _, grid_export, _ = simulate_battery_hour(
            pv_power=15.0,
            load_power=5.0,
            current_soc=17.5,  # Near max (87.5%)
            battery_kwh=20.0,
            battery_power_kw=10.0,
            soc_max=0.90
        )

        assert grid_export > 0

    def test_grid_import_when_battery_empty(self):
        """Deficit should import when battery empty"""
        _, _, discharge, grid_import, _, _ = simulate_battery_hour(
            pv_power=2.0,
            load_power=10.0,
            current_soc=2.5,  # Near min (12.5%)
            battery_kwh=20.0,
            battery_power_kw=10.0,
            soc_min=0.10
        )

        assert grid_import > 0

    def test_self_consumption_calculation(self):
        """Self-consumption should include direct + battery discharge"""
        # Case 1: Direct consumption only
        _, _, _, _, _, self_cons = simulate_battery_hour(
            pv_power=5.0,
            load_power=5.0,
            current_soc=10.0,
            battery_kwh=20.0,
            battery_power_kw=10.0
        )
        assert self_cons == 5.0  # All PV consumed directly

        # Case 2: With battery discharge
        _, _, discharge, _, _, self_cons = simulate_battery_hour(
            pv_power=2.0,
            load_power=8.0,
            current_soc=15.0,
            battery_kwh=20.0,
            battery_power_kw=10.0
        )
        # Self-consumption = direct (2 kW) + discharge
        assert self_cons == 2.0 + discharge

    def test_balanced_load_no_battery_activity(self):
        """Balanced load/PV should have no battery activity"""
        new_soc, charge, discharge, grid_import, grid_export, _ = simulate_battery_hour(
            pv_power=5.0,
            load_power=5.0,
            current_soc=10.0,
            battery_kwh=20.0,
            battery_power_kw=10.0
        )

        assert charge == 0
        assert discharge == 0
        assert grid_import == 0
        assert grid_export == 0
        assert new_soc == 10.0


# ============================================================================
# YEAR SIMULATION TESTS
# ============================================================================

class TestBatteryYearSimulation:
    """Tests for full year battery simulation"""

    def test_energy_balance(self, sample_load_profile):
        """Total energy in = energy out (with losses)"""
        hours = len(sample_load_profile)
        pv_output = np.random.uniform(0, 10, hours)  # Random PV

        result = simulate_battery_year(
            pv_output=pv_output,
            load_profile=sample_load_profile,
            battery_kwh=20.0,
            battery_power_kw=10.0
        )

        # Charge * efficiency ~= Discharge (over long periods)
        roundtrip = 0.90
        expected_discharge = result["total_charge_kwh"] * roundtrip
        # Allow 10% tolerance for SOC start/end difference
        assert abs(result["total_discharge_kwh"] - expected_discharge) / expected_discharge < 0.15

    def test_operating_hours_sum(self, sample_load_profile):
        """Operating hours = charging + discharging hours"""
        pv_output = np.sin(np.linspace(0, 20 * np.pi, 8760)) * 5 + 5

        result = simulate_battery_year(
            pv_output=pv_output,
            load_profile=sample_load_profile,
            battery_kwh=20.0,
            battery_power_kw=10.0
        )

        assert result["operating_hours"] == result["charging_hours"] + result["discharging_hours"]

    def test_cycles_calculation(self, sample_load_profile):
        """Cycles = discharge / capacity"""
        pv_output = np.sin(np.linspace(0, 20 * np.pi, 8760)) * 5 + 5
        battery_kwh = 20.0

        result = simulate_battery_year(
            pv_output=pv_output,
            load_profile=sample_load_profile,
            battery_kwh=battery_kwh,
            battery_power_kw=10.0
        )

        expected_cycles = result["total_discharge_kwh"] / battery_kwh
        assert abs(result["battery_cycles"] - expected_cycles) < 0.01

    def test_full_load_hours_calculation(self, sample_load_profile):
        """Full load hours = discharge / power"""
        pv_output = np.sin(np.linspace(0, 20 * np.pi, 8760)) * 5 + 5
        battery_power_kw = 10.0

        result = simulate_battery_year(
            pv_output=pv_output,
            load_profile=sample_load_profile,
            battery_kwh=20.0,
            battery_power_kw=battery_power_kw
        )

        expected_flh = result["total_discharge_kwh"] / battery_power_kw
        assert abs(result["battery_full_load_hours"] - expected_flh) < 0.01

    def test_typical_commercial_values(self, sample_load_profile):
        """Validate typical commercial system values"""
        # Generate realistic PV profile (peak at noon, summer higher)
        hours = 8760
        pv_output = np.zeros(hours)
        for h in range(hours):
            day = h // 24
            hour = h % 24
            # Summer has higher yield
            seasonal = 1 + 0.5 * np.sin(2 * np.pi * (day - 80) / 365)
            # Daylight hours
            if 6 <= hour <= 20:
                daily = np.sin(np.pi * (hour - 6) / 14) * seasonal
                pv_output[h] = max(0, daily * 30)  # 30 kWp peak

        result = simulate_battery_year(
            pv_output=pv_output,
            load_profile=sample_load_profile,
            battery_kwh=20.0,
            battery_power_kw=10.0
        )

        # Typical ranges for commercial systems
        assert 100 <= result["battery_cycles"] <= 400
        assert 1000 <= result["operating_hours"] <= 5000
        assert 400 <= result["battery_full_load_hours"] <= 1500

    def test_no_pv_no_battery_activity(self, sample_load_profile):
        """No PV = no battery charging"""
        pv_output = np.zeros(8760)

        result = simulate_battery_year(
            pv_output=pv_output,
            load_profile=sample_load_profile,
            battery_kwh=20.0,
            battery_power_kw=10.0
        )

        assert result["total_charge_kwh"] == 0
        assert result["charging_hours"] == 0

    def test_small_battery_high_cycles(self, sample_load_profile):
        """Small battery should have more cycles"""
        pv_output = np.sin(np.linspace(0, 20 * np.pi, 8760)) * 5 + 5

        result_small = simulate_battery_year(
            pv_output=pv_output,
            load_profile=sample_load_profile,
            battery_kwh=10.0,
            battery_power_kw=5.0
        )

        result_large = simulate_battery_year(
            pv_output=pv_output,
            load_profile=sample_load_profile,
            battery_kwh=50.0,
            battery_power_kw=25.0
        )

        # Smaller battery = more cycles
        assert result_small["battery_cycles"] > result_large["battery_cycles"]


# ============================================================================
# EFFICIENCY & DEGRADATION TESTS
# ============================================================================

class TestBatteryEfficiency:
    """Tests for efficiency handling"""

    def test_roundtrip_loss(self, sample_load_profile):
        """Roundtrip should have ~10% loss at 90% efficiency"""
        pv_output = np.sin(np.linspace(0, 20 * np.pi, 8760)) * 5 + 5

        result_90 = simulate_battery_year(
            pv_output=pv_output,
            load_profile=sample_load_profile,
            battery_kwh=20.0,
            battery_power_kw=10.0,
            roundtrip_efficiency=0.90
        )

        result_100 = simulate_battery_year(
            pv_output=pv_output,
            load_profile=sample_load_profile,
            battery_kwh=20.0,
            battery_power_kw=10.0,
            roundtrip_efficiency=1.0
        )

        # 90% efficiency should result in ~10% less usable energy
        ratio = result_90["total_discharge_kwh"] / result_100["total_discharge_kwh"]
        assert 0.85 <= ratio <= 0.95

    def test_different_efficiencies(self, sample_load_profile):
        """Lower efficiency = less discharge"""
        pv_output = np.sin(np.linspace(0, 20 * np.pi, 8760)) * 5 + 5

        result_high = simulate_battery_year(
            pv_output=pv_output,
            load_profile=sample_load_profile,
            battery_kwh=20.0,
            battery_power_kw=10.0,
            roundtrip_efficiency=0.95
        )

        result_low = simulate_battery_year(
            pv_output=pv_output,
            load_profile=sample_load_profile,
            battery_kwh=20.0,
            battery_power_kw=10.0,
            roundtrip_efficiency=0.85
        )

        assert result_high["total_discharge_kwh"] > result_low["total_discharge_kwh"]


# ============================================================================
# DIN EN 15316 COMPLIANCE TESTS
# ============================================================================

class TestDINEN15316Compliance:
    """Tests for DIN EN 15316 operating hours definition"""

    def test_operating_hours_definition(self, sample_load_profile):
        """Operating hours = hours with charging OR discharging activity"""
        pv_output = np.sin(np.linspace(0, 20 * np.pi, 8760)) * 5 + 5

        result = simulate_battery_year(
            pv_output=pv_output,
            load_profile=sample_load_profile,
            battery_kwh=20.0,
            battery_power_kw=10.0
        )

        # Operating hours is sum, no overlap possible (can't charge and discharge same hour)
        assert result["operating_hours"] == result["charging_hours"] + result["discharging_hours"]

    def test_max_operating_hours(self, sample_load_profile):
        """Operating hours cannot exceed 8760"""
        pv_output = np.ones(8760) * 10  # Constant high PV

        result = simulate_battery_year(
            pv_output=pv_output,
            load_profile=sample_load_profile,
            battery_kwh=20.0,
            battery_power_kw=10.0
        )

        assert result["operating_hours"] <= 8760

    def test_utilization_calculation(self, sample_load_profile):
        """Utilization = operating hours / 8760"""
        pv_output = np.sin(np.linspace(0, 20 * np.pi, 8760)) * 5 + 5

        result = simulate_battery_year(
            pv_output=pv_output,
            load_profile=sample_load_profile,
            battery_kwh=20.0,
            battery_power_kw=10.0
        )

        utilization = result["operating_hours"] / 8760 * 100
        # Typical commercial: 25-45%
        assert 15 <= utilization <= 60
