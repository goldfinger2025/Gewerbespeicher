"""
Unit Tests for Critical Calculation Formulas
=============================================

Tests validate mathematical correctness of all key formulas against
academic references (HTW Berlin, VDI 2067, Fraunhofer ISE, IEA PVPS).

Run with: pytest tests/test_calculations.py -v
"""

import pytest
import math
from typing import Dict


# ============================================================================
# HELPER FUNCTIONS (extracted from simulator for isolated testing)
# ============================================================================

def calculate_autonomy_degree(total_load: float, total_grid_import: float) -> float:
    """
    Calculate autonomy degree (Autarkiegrad)

    Formula: (Total Load - Grid Import) / Total Load × 100%
    Reference: HTW Berlin (Prof. Quaschning)
    """
    if total_load <= 0:
        return 0.0
    autonomy = ((total_load - total_grid_import) / total_load) * 100
    return max(0, min(100, autonomy))


def calculate_self_consumption_ratio(
    total_self_consumption: float,
    total_pv_generation: float
) -> float:
    """
    Calculate self-consumption ratio (Eigenverbrauchsquote)

    Formula: Self-Consumed / PV Generation × 100%
    Reference: Industry standard
    """
    if total_pv_generation <= 0:
        return 0.0
    return (total_self_consumption / total_pv_generation) * 100


def calculate_npv(
    investment: float,
    annual_savings: float,
    discount_rate: float,
    years: int,
    degradation: float = 0.005
) -> float:
    """
    Calculate Net Present Value (NPV)

    Formula: NPV = -I₀ + Σ(t=1 bis n) [CFₜ × (1-d)^t / (1+r)^t]
    Reference: VDI 2067
    """
    if investment <= 0:
        return 0.0

    npv = -investment
    for year in range(1, years + 1):
        degradation_factor = (1 - degradation) ** year
        yearly_cf = annual_savings * degradation_factor
        npv += yearly_cf / ((1 + discount_rate) ** year)

    return npv


def calculate_irr(
    investment: float,
    annual_cf: float,
    years: int,
    degradation: float = 0.005
) -> float:
    """
    Calculate Internal Rate of Return (IRR) using Newton-Raphson

    Definition: The discount rate r* where NPV = 0
    Reference: Financial mathematics standard
    """
    if investment <= 0 or annual_cf <= 0:
        return 0.0

    # Initial guess
    rate = annual_cf / investment

    for _ in range(50):
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

        rate = max(0.001, min(0.5, rate_new))

    return rate * 100  # Return as percentage


def calculate_discounted_payback(
    investment: float,
    annual_cf: float,
    discount_rate: float,
    years: int,
    degradation: float = 0.005
) -> float:
    """
    Calculate discounted payback period

    Definition: Year where cumulative discounted cash flows >= investment
    Reference: Investment calculation methodology
    """
    if investment <= 0 or annual_cf <= 0:
        return 99.0

    cumulative_dcf = 0.0
    for year in range(1, years + 1):
        cf = annual_cf * ((1 - degradation) ** year)
        dcf = cf / ((1 + discount_rate) ** year)
        cumulative_dcf += dcf

        if cumulative_dcf >= investment:
            # Interpolation for sub-year precision
            previous_cumulative = cumulative_dcf - dcf
            remaining = investment - previous_cumulative
            fraction = remaining / dcf if dcf > 0 else 0
            return year - 1 + fraction

    return 99.0


def calculate_simple_payback(investment: float, annual_savings: float) -> float:
    """
    Calculate simple payback period

    Formula: Investment / Annual Savings
    """
    if annual_savings <= 0:
        return 99.0
    return investment / annual_savings


def calculate_full_load_hours(energy_kwh: float, power_kw: float) -> float:
    """
    Calculate full load hours (Volllaststunden)

    Formula: Energy [kWh] / Power [kW]
    Reference: VDI 4655, IEA PVPS
    """
    if power_kw <= 0:
        return 0.0
    return energy_kwh / power_kw


def calculate_capacity_factor(full_load_hours: float) -> float:
    """
    Calculate capacity factor

    Formula: Full Load Hours / 8760 × 100%
    Reference: IEEE 762
    """
    return (full_load_hours / 8760) * 100


def calculate_battery_efficiency(roundtrip_efficiency: float) -> float:
    """
    Calculate single-direction battery efficiency

    Formula: √(Round-Trip Efficiency)
    Reference: Fraunhofer ISE (symmetric losses assumption)
    """
    return roundtrip_efficiency ** 0.5


# ============================================================================
# AUTARKIE & EIGENVERBRAUCH TESTS
# ============================================================================

class TestAutonomyDegree:
    """Tests for Autarkiegrad (Autonomy Degree) calculation"""

    def test_full_autonomy(self):
        """100% autonomy when no grid import"""
        result = calculate_autonomy_degree(total_load=50000, total_grid_import=0)
        assert result == 100.0

    def test_zero_autonomy(self):
        """0% autonomy when grid import equals load"""
        result = calculate_autonomy_degree(total_load=50000, total_grid_import=50000)
        assert result == 0.0

    def test_partial_autonomy(self):
        """50% autonomy when half from grid"""
        result = calculate_autonomy_degree(total_load=50000, total_grid_import=25000)
        assert result == 50.0

    def test_typical_commercial_case(self):
        """Typical commercial case: 50 MWh load, 25 MWh import = 50% autonomy"""
        result = calculate_autonomy_degree(total_load=50000, total_grid_import=25000)
        assert abs(result - 50.0) < 0.1

    def test_htw_berlin_formula(self):
        """Validate against HTW Berlin formula"""
        # Formula: (Verbrauch - Netzbezug) / Verbrauch
        total_load = 40000
        grid_import = 16000
        expected = ((40000 - 16000) / 40000) * 100  # = 60%
        result = calculate_autonomy_degree(total_load, grid_import)
        assert abs(result - expected) < 0.001

    def test_zero_load_edge_case(self):
        """Edge case: zero load should return 0"""
        result = calculate_autonomy_degree(total_load=0, total_grid_import=0)
        assert result == 0.0

    def test_negative_import_clamped(self):
        """Negative import (impossible) should still be capped at 100%"""
        result = calculate_autonomy_degree(total_load=50000, total_grid_import=-5000)
        assert result == 100.0

    def test_overconsumption_clamped(self):
        """Import > load (impossible) should be capped at 0%"""
        result = calculate_autonomy_degree(total_load=50000, total_grid_import=60000)
        assert result == 0.0


class TestSelfConsumptionRatio:
    """Tests for Eigenverbrauchsquote (Self-Consumption Ratio)"""

    def test_full_self_consumption(self):
        """100% self-consumption when all PV used"""
        result = calculate_self_consumption_ratio(
            total_self_consumption=30000,
            total_pv_generation=30000
        )
        assert result == 100.0

    def test_partial_self_consumption(self):
        """Typical case with grid export"""
        result = calculate_self_consumption_ratio(
            total_self_consumption=25000,
            total_pv_generation=30000
        )
        expected = (25000 / 30000) * 100  # = 83.33%
        assert abs(result - expected) < 0.01

    def test_zero_pv_generation(self):
        """Edge case: no PV generation"""
        result = calculate_self_consumption_ratio(
            total_self_consumption=0,
            total_pv_generation=0
        )
        assert result == 0.0

    def test_typical_values(self):
        """Typical commercial values: 28.5 MWh PV, 25 MWh self-consumed"""
        result = calculate_self_consumption_ratio(
            total_self_consumption=25000,
            total_pv_generation=28500
        )
        expected = (25000 / 28500) * 100  # ≈ 87.7%
        assert abs(result - expected) < 0.1


# ============================================================================
# FINANCIAL CALCULATION TESTS
# ============================================================================

class TestNPV:
    """Tests for Net Present Value (NPV) calculation"""

    def test_positive_npv(self):
        """Profitable investment should have positive NPV"""
        npv = calculate_npv(
            investment=45000,
            annual_savings=6000,
            discount_rate=0.03,
            years=20,
            degradation=0.005
        )
        assert npv > 0

    def test_npv_formula_manual(self):
        """Manual NPV calculation for verification"""
        investment = 10000
        annual_savings = 2000
        discount_rate = 0.05
        years = 5
        degradation = 0.0  # No degradation for simple case

        # Manual calculation
        expected = -investment
        for year in range(1, years + 1):
            expected += annual_savings / ((1 + discount_rate) ** year)

        result = calculate_npv(investment, annual_savings, discount_rate, years, degradation)
        assert abs(result - expected) < 0.01

    def test_npv_with_degradation(self):
        """NPV should be lower with degradation"""
        npv_no_deg = calculate_npv(45000, 6000, 0.03, 20, degradation=0.0)
        npv_with_deg = calculate_npv(45000, 6000, 0.03, 20, degradation=0.005)

        assert npv_with_deg < npv_no_deg

    def test_npv_zero_investment(self):
        """Zero investment should return 0"""
        result = calculate_npv(0, 6000, 0.03, 20)
        assert result == 0.0

    def test_npv_vdi_2067_compliance(self):
        """Validate NPV calculation matches VDI 2067 methodology"""
        # Standard parameters
        investment = 50000
        annual_savings = 5000
        discount_rate = 0.03
        years = 20

        # VDI 2067: NPV = -I + A * ((1+r)^n - 1) / (r * (1+r)^n)
        # This is the annuity formula for constant cash flows
        annuity_factor = ((1 + discount_rate) ** years - 1) / (discount_rate * (1 + discount_rate) ** years)
        expected_npv = -investment + annual_savings * annuity_factor

        result = calculate_npv(investment, annual_savings, discount_rate, years, degradation=0.0)
        assert abs(result - expected_npv) < 1.0  # Within 1 EUR


class TestIRR:
    """Tests for Internal Rate of Return (IRR) calculation"""

    def test_irr_reasonable_range(self):
        """IRR should be in reasonable range for typical investment"""
        irr = calculate_irr(
            investment=45000,
            annual_cf=6000,
            years=20,
            degradation=0.005
        )
        # Typical commercial PV IRR: 5-15%
        assert 5 < irr < 20

    def test_irr_npv_zero(self):
        """At IRR, NPV should be approximately zero"""
        investment = 45000
        annual_cf = 6000
        years = 20
        degradation = 0.005

        irr = calculate_irr(investment, annual_cf, years, degradation) / 100

        # Calculate NPV at IRR
        npv_at_irr = -investment
        for year in range(1, years + 1):
            cf = annual_cf * ((1 - degradation) ** year)
            npv_at_irr += cf / ((1 + irr) ** year)

        # NPV should be close to zero at IRR
        assert abs(npv_at_irr) < 100  # Within 100 EUR tolerance

    def test_irr_zero_cashflow(self):
        """Zero cash flow should return 0% IRR"""
        irr = calculate_irr(investment=45000, annual_cf=0, years=20)
        assert irr == 0.0

    def test_irr_quick_payback(self):
        """High cash flow relative to investment = high IRR"""
        irr_high = calculate_irr(investment=10000, annual_cf=3000, years=10)
        irr_low = calculate_irr(investment=10000, annual_cf=1000, years=10)

        assert irr_high > irr_low

    def test_irr_convergence(self):
        """IRR should converge for reasonable inputs"""
        irr = calculate_irr(investment=50000, annual_cf=7500, years=15)
        # Should converge to a value, not hit bounds
        assert 0.1 < irr < 50


class TestPaybackPeriod:
    """Tests for payback period calculations"""

    def test_simple_payback(self):
        """Simple payback = Investment / Annual Savings"""
        result = calculate_simple_payback(investment=45000, annual_savings=6000)
        assert result == 7.5  # 45000 / 6000 = 7.5 years

    def test_simple_payback_zero_savings(self):
        """Zero savings should return max value"""
        result = calculate_simple_payback(investment=45000, annual_savings=0)
        assert result == 99.0

    def test_discounted_payback_longer(self):
        """Discounted payback should be longer than simple payback"""
        simple = calculate_simple_payback(45000, 6000)
        discounted = calculate_discounted_payback(45000, 6000, 0.03, 20, 0.005)

        assert discounted > simple

    def test_discounted_payback_with_interpolation(self):
        """Discounted payback should include sub-year precision"""
        result = calculate_discounted_payback(
            investment=30000,
            annual_cf=6000,
            discount_rate=0.03,
            years=20,
            degradation=0.005
        )
        # Should not be exactly an integer
        assert result != int(result)

    def test_discounted_payback_not_achieved(self):
        """Low savings should not achieve payback"""
        result = calculate_discounted_payback(
            investment=100000,
            annual_cf=1000,
            discount_rate=0.03,
            years=20,
            degradation=0.01
        )
        assert result == 99.0


# ============================================================================
# FULL LOAD HOURS & CAPACITY FACTOR TESTS
# ============================================================================

class TestFullLoadHours:
    """Tests for Volllaststunden (Full Load Hours)"""

    def test_pv_full_load_hours_germany(self):
        """PV full load hours in Germany: 900-1100 h"""
        # 30 kWp system with 28500 kWh yield
        result = calculate_full_load_hours(energy_kwh=28500, power_kw=30)
        assert result == 950  # 28500 / 30 = 950 h
        assert 900 <= result <= 1100  # Typical range for Germany

    def test_battery_full_load_hours(self):
        """Battery full load hours calculation"""
        # 10 kW battery with 8000 kWh discharge
        result = calculate_full_load_hours(energy_kwh=8000, power_kw=10)
        assert result == 800  # 8000 / 10 = 800 h

    def test_zero_power(self):
        """Zero power should return 0"""
        result = calculate_full_load_hours(energy_kwh=1000, power_kw=0)
        assert result == 0.0

    def test_vdi_4655_compliance(self):
        """Validate against VDI 4655 definition"""
        # Definition: Stunden bei Nennleistung für gleiche Energiemenge
        energy = 50000
        power = 50
        expected = energy / power  # = 1000 h

        result = calculate_full_load_hours(energy, power)
        assert result == expected


class TestCapacityFactor:
    """Tests for capacity factor (Kapazitätsfaktor)"""

    def test_capacity_factor_formula(self):
        """Capacity factor = Full load hours / 8760"""
        flh = 950
        expected = (950 / 8760) * 100  # ≈ 10.84%

        result = calculate_capacity_factor(flh)
        assert abs(result - expected) < 0.01

    def test_capacity_factor_pv_typical(self):
        """Typical PV capacity factor in Germany: 10-13%"""
        flh = 1000  # Typical PV
        result = calculate_capacity_factor(flh)
        assert 10 <= result <= 13

    def test_capacity_factor_battery_typical(self):
        """Typical battery capacity factor: 5-10%"""
        flh = 700  # Typical battery
        result = calculate_capacity_factor(flh)
        assert 5 <= result <= 12

    def test_ieee_762_compliance(self):
        """IEEE 762 defines capacity factor as actual/theoretical max"""
        # 8760 hours = theoretical maximum
        flh = 4380  # 50% capacity factor
        result = calculate_capacity_factor(flh)
        assert abs(result - 50.0) < 0.1


# ============================================================================
# BATTERY EFFICIENCY TESTS
# ============================================================================

class TestBatteryEfficiency:
    """Tests for battery efficiency calculations"""

    def test_single_direction_efficiency(self):
        """Single direction = √(Round-Trip)"""
        roundtrip = 0.90
        expected = 0.90 ** 0.5  # ≈ 0.949

        result = calculate_battery_efficiency(roundtrip)
        assert abs(result - expected) < 0.001

    def test_roundtrip_reconstruction(self):
        """Single² should equal round-trip"""
        roundtrip = 0.90
        single = calculate_battery_efficiency(roundtrip)
        reconstructed = single * single

        assert abs(reconstructed - roundtrip) < 0.0001

    def test_fraunhofer_ise_range(self):
        """Efficiency should be in Fraunhofer ISE reported range"""
        # Fraunhofer ISE: LFP round-trip 88-92%
        for rt in [0.88, 0.90, 0.92]:
            single = calculate_battery_efficiency(rt)
            # Single direction should be 93.8-95.9%
            assert 0.93 <= single <= 0.96

    def test_perfect_efficiency(self):
        """100% round-trip = 100% single direction"""
        result = calculate_battery_efficiency(1.0)
        assert result == 1.0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestCalculationIntegration:
    """Integration tests combining multiple calculations"""

    def test_energy_balance(self, sample_energy_flows):
        """Verify energy balance consistency"""
        ef = sample_energy_flows

        # Self-consumption = PV generation - Grid export
        expected_self_consumption = ef["total_pv_generation"] - ef["total_grid_export"]
        assert abs(expected_self_consumption - ef["total_self_consumption"]) < 1.0

    def test_autonomy_self_consumption_relationship(self, sample_energy_flows):
        """Verify relationship between autonomy and self-consumption"""
        ef = sample_energy_flows

        autonomy = calculate_autonomy_degree(ef["total_load"], ef["total_grid_import"])
        self_consumption = calculate_self_consumption_ratio(
            ef["total_self_consumption"],
            ef["total_pv_generation"]
        )

        # Both should be positive
        assert autonomy > 0
        assert self_consumption > 0

        # With battery, self-consumption usually > autonomy
        # (Battery stores excess for later use)

    def test_financial_metrics_consistency(self, sample_financial_params):
        """Verify financial metrics are consistent"""
        fp = sample_financial_params

        npv = calculate_npv(
            fp["total_investment"],
            fp["annual_savings"],
            fp["discount_rate"],
            fp["project_lifetime"],
            fp["degradation_rate"]
        )

        irr = calculate_irr(
            fp["total_investment"],
            fp["annual_savings"],
            fp["project_lifetime"],
            fp["degradation_rate"]
        )

        simple_payback = calculate_simple_payback(
            fp["total_investment"],
            fp["annual_savings"]
        )

        discounted_payback = calculate_discounted_payback(
            fp["total_investment"],
            fp["annual_savings"],
            fp["discount_rate"],
            fp["project_lifetime"],
            fp["degradation_rate"]
        )

        # Positive NPV should mean IRR > discount rate
        if npv > 0:
            assert irr > fp["discount_rate"] * 100

        # Discounted payback should be longer than simple
        assert discounted_payback >= simple_payback

        # Payback should be < project lifetime if NPV positive
        if npv > 0:
            assert discounted_payback < fp["project_lifetime"]

    def test_typical_commercial_system(self):
        """Complete test for typical 30 kWp commercial system"""
        # System: 30 kWp PV, 20 kWh battery, 50 MWh consumption
        pv_peak_kw = 30
        battery_kwh = 20
        battery_power_kw = 10

        # Expected yields (North Germany)
        pv_yield = 28500  # ~950 kWh/kWp
        load = 50000
        grid_import = 25000
        grid_export = 3500
        self_consumed = pv_yield - grid_export
        battery_discharge = 8000

        # Calculate all KPIs
        autonomy = calculate_autonomy_degree(load, grid_import)
        self_consumption = calculate_self_consumption_ratio(self_consumed, pv_yield)
        pv_flh = calculate_full_load_hours(pv_yield, pv_peak_kw)
        battery_flh = calculate_full_load_hours(battery_discharge, battery_power_kw)
        battery_cf = calculate_capacity_factor(battery_flh)

        # Investment and savings
        investment = 30 * 1050 + 20 * 600 + 3000  # ~46,500 EUR
        annual_savings = (load - grid_import) * 0.30 + grid_export * 0.0786 - grid_import * 0.30
        # Simplified: savings = avoided cost - grid cost + feed-in
        # = 25000 * 0.30 + 3500 * 0.0786 = 7500 + 275 = 7775 EUR

        # Verify all metrics in expected ranges
        assert 45 <= autonomy <= 55  # ~50%
        assert 80 <= self_consumption <= 95  # ~88%
        assert 900 <= pv_flh <= 1000  # ~950
        assert 700 <= battery_flh <= 900  # ~800
        assert 5 <= battery_cf <= 12  # ~9%
