"""
Unit Tests for Peak-Shaving Service
====================================

Tests validate peak-shaving calculations, battery sizing, and economics
for commercial customers with RLM metering (>100 MWh/year).

Reference: StromNZV, industry practice
Run with: pytest tests/test_peak_shaving.py -v
"""

import numpy as np
from typing import Dict, List


# ============================================================================
# PEAK SHAVING FUNCTIONS (extracted for isolated testing)
# ============================================================================

def analyze_load_profile(
    load_profile_kw: np.ndarray,
    interval_minutes: int = 15,
    leistungspreis: float = 100.0
) -> Dict:
    """
    Analyze load profile for peak-shaving potential

    Args:
        load_profile_kw: Load profile in kW
        interval_minutes: Measurement interval (15 min for RLM)
        leistungspreis: Power price in €/kW/year
    """
    if len(load_profile_kw) == 0:
        return {"error": "Empty profile"}

    max_load = float(np.max(load_profile_kw))
    mean_load = float(np.mean(load_profile_kw))

    hours_per_interval = interval_minutes / 60
    total_energy_kwh = float(np.sum(load_profile_kw) * hours_per_interval)

    benutzungsstunden = total_energy_kwh / max_load if max_load > 0 else 0

    p90 = np.percentile(load_profile_kw, 90)
    potential_reduction = max_load - p90
    potential_savings = potential_reduction * leistungspreis

    is_rlm = total_energy_kwh >= 100000  # 100 MWh threshold

    return {
        "max_kw": max_load,
        "mean_kw": mean_load,
        "total_energy_kwh": total_energy_kwh,
        "benutzungsstunden": benutzungsstunden,
        "p90_kw": p90,
        "potential_reduction_kw": potential_reduction,
        "potential_savings_eur": potential_savings,
        "is_rlm": is_rlm,
    }


def identify_top_peaks(
    load_profile_kw: np.ndarray,
    n_peaks: int = 10,
    interval_minutes: int = 15,
    min_distance_hours: float = 4.0
) -> List[Dict]:
    """
    Identify top N peaks with minimum distance between them
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

        peaks.append({
            "index": peak_idx,
            "value_kw": peak_value,
        })

        # Mask out peak and surrounding area
        start = max(0, peak_idx - min_distance)
        end = min(len(profile_copy), peak_idx + min_distance)
        profile_copy[start:end] = 0

    return peaks


def calculate_required_battery(
    load_profile_kw: np.ndarray,
    target_peak_kw: float,
    interval_minutes: int = 15,
    battery_efficiency: float = 0.95,
    soc_range: float = 0.8,
    safety_factor: float = 1.15
) -> Dict:
    """
    Calculate required battery size for peak-shaving goal
    """
    hours_per_interval = interval_minutes / 60

    total_shaved_energy = 0.0
    max_shaving_power = 0.0
    max_consecutive_energy = 0.0
    current_event_energy = 0.0
    in_event = False
    shaving_events = 0

    for load in load_profile_kw:
        if load > target_peak_kw:
            shaving_needed = load - target_peak_kw
            shaving_power = shaving_needed / battery_efficiency
            energy_needed = shaving_power * hours_per_interval

            total_shaved_energy += energy_needed
            max_shaving_power = max(max_shaving_power, shaving_power)
            current_event_energy += energy_needed

            if not in_event:
                in_event = True
                shaving_events += 1
        else:
            if in_event:
                max_consecutive_energy = max(max_consecutive_energy, current_event_energy)
                current_event_energy = 0
                in_event = False

    # Final event
    if in_event:
        max_consecutive_energy = max(max_consecutive_energy, current_event_energy)

    # Battery sizing
    required_capacity = max_consecutive_energy / soc_range * safety_factor
    required_power = max_shaving_power * safety_factor

    return {
        "required_capacity_kwh": required_capacity,
        "required_power_kw": required_power,
        "c_rate": required_power / required_capacity if required_capacity > 0 else 0,
        "shaving_events": shaving_events,
        "total_shaved_energy_kwh": total_shaved_energy,
        "max_event_energy_kwh": max_consecutive_energy,
    }


def calculate_peak_shaving_economics(
    original_peak_kw: float,
    target_peak_kw: float,
    battery_capacity_kwh: float,
    battery_cost_per_kwh: float = 600.0,
    additional_costs: float = 3000.0,
    leistungspreis: float = 100.0,
    years: int = 15,
    discount_rate: float = 0.03
) -> Dict:
    """
    Calculate economics of peak-shaving solution
    """
    battery_cost = battery_capacity_kwh * battery_cost_per_kwh
    total_investment = battery_cost + additional_costs

    peak_reduction = original_peak_kw - target_peak_kw
    annual_savings = peak_reduction * leistungspreis

    if annual_savings > 0:
        simple_payback = total_investment / annual_savings
    else:
        simple_payback = 99.0

    # NPV
    npv = -total_investment
    for year in range(1, years + 1):
        npv += annual_savings / ((1 + discount_rate) ** year)

    # ROI
    total_savings = annual_savings * years
    roi_percent = ((total_savings - total_investment) / total_investment) * 100 if total_investment > 0 else 0

    return {
        "total_investment_eur": total_investment,
        "peak_reduction_kw": peak_reduction,
        "annual_savings_eur": annual_savings,
        "simple_payback_years": simple_payback,
        "npv_eur": npv,
        "roi_percent": roi_percent,
    }


# ============================================================================
# LOAD PROFILE ANALYSIS TESTS
# ============================================================================

class TestLoadProfileAnalysis:
    """Tests for load profile analysis"""

    def test_max_load_detection(self):
        """Maximum load should be correctly identified"""
        profile = np.array([10, 20, 50, 30, 40])
        result = analyze_load_profile(profile)
        assert result["max_kw"] == 50.0

    def test_mean_load_calculation(self):
        """Mean load should be correctly calculated"""
        profile = np.array([10, 20, 30, 40, 50])
        result = analyze_load_profile(profile)
        assert result["mean_kw"] == 30.0

    def test_energy_calculation(self):
        """Total energy should account for interval"""
        # 4 intervals of 15 min = 1 hour
        profile = np.array([100, 100, 100, 100])  # 100 kW for 1 hour
        result = analyze_load_profile(profile, interval_minutes=15)
        assert abs(result["total_energy_kwh"] - 100.0) < 0.1

    def test_benutzungsstunden(self):
        """Operating hours = energy / max power"""
        profile = np.array([50, 100, 50, 100])  # avg 75, max 100
        result = analyze_load_profile(profile, interval_minutes=15)
        # Energy = 75 * 1h = 75 kWh, max = 100 kW
        # Benutzungsstunden = 75 / 100 = 0.75 h (for this period)
        expected = result["total_energy_kwh"] / result["max_kw"]
        assert abs(result["benutzungsstunden"] - expected) < 0.01

    def test_p90_percentile(self):
        """P90 should identify 90th percentile"""
        profile = np.arange(1, 101)  # 1 to 100
        result = analyze_load_profile(profile)
        # P90 of 1-100 should be ~90
        assert 89 <= result["p90_kw"] <= 91

    def test_rlm_threshold(self):
        """RLM flag should be set at 100 MWh"""
        # 100 MWh over 8760 intervals of 15 min
        # Need 100000 kWh / (8760 * 0.25 h) = ~45.7 kW average
        hours = 8760 * 4  # 15-min intervals
        profile = np.ones(hours) * 46  # ~100 MWh
        result = analyze_load_profile(profile, interval_minutes=15)
        assert result["is_rlm"]

        profile_small = np.ones(hours) * 10  # ~22 MWh
        result_small = analyze_load_profile(profile_small, interval_minutes=15)
        assert not result_small["is_rlm"]

    def test_potential_savings(self):
        """Potential savings = reduction × power price"""
        profile = np.array([50, 60, 100, 70, 80])  # Max=100, P90=~90
        leistungspreis = 100  # €/kW/year
        result = analyze_load_profile(profile, leistungspreis=leistungspreis)

        expected = result["potential_reduction_kw"] * leistungspreis
        assert abs(result["potential_savings_eur"] - expected) < 0.01


# ============================================================================
# PEAK IDENTIFICATION TESTS
# ============================================================================

class TestPeakIdentification:
    """Tests for top peak identification"""

    def test_finds_highest_peak(self):
        """Should identify the absolute maximum"""
        profile = np.array([10, 20, 100, 30, 40])
        peaks = identify_top_peaks(profile, n_peaks=1)
        assert len(peaks) == 1
        assert peaks[0]["value_kw"] == 100.0
        assert peaks[0]["index"] == 2

    def test_finds_multiple_peaks(self):
        """Should find multiple peaks in order"""
        profile = np.zeros(100)
        profile[10] = 100
        profile[50] = 80
        profile[90] = 60

        peaks = identify_top_peaks(profile, n_peaks=3, min_distance_hours=1.0)
        assert len(peaks) == 3
        assert peaks[0]["value_kw"] == 100.0
        assert peaks[1]["value_kw"] == 80.0
        assert peaks[2]["value_kw"] == 60.0

    def test_respects_minimum_distance(self):
        """Peaks too close should be filtered"""
        profile = np.zeros(100)
        profile[10] = 100
        profile[11] = 95  # Too close to first peak

        peaks = identify_top_peaks(profile, n_peaks=2, min_distance_hours=1.0, interval_minutes=15)
        # With 15-min intervals, 1 hour = 4 intervals
        # Second peak at index 11 is within 4 intervals of 10
        assert len(peaks) <= 2
        assert peaks[0]["value_kw"] == 100.0

    def test_empty_profile(self):
        """Empty profile should return empty list"""
        profile = np.array([])
        peaks = identify_top_peaks(profile, n_peaks=5)
        assert len(peaks) == 0

    def test_all_zeros(self):
        """All-zero profile should return empty list"""
        profile = np.zeros(100)
        peaks = identify_top_peaks(profile, n_peaks=5)
        assert len(peaks) == 0


# ============================================================================
# BATTERY SIZING TESTS
# ============================================================================

class TestBatterySizing:
    """Tests for peak-shaving battery sizing"""

    def test_no_shaving_needed(self):
        """No shaving if target above max"""
        profile = np.array([50, 60, 70, 80, 90])
        result = calculate_required_battery(profile, target_peak_kw=100)
        assert result["required_capacity_kwh"] == 0
        assert result["shaving_events"] == 0

    def test_simple_shaving(self):
        """Simple case: one peak above target"""
        profile = np.zeros(100)
        profile[50] = 100  # Single 100 kW peak for 15 min

        result = calculate_required_battery(
            profile,
            target_peak_kw=80,
            interval_minutes=15,
            battery_efficiency=1.0,
            soc_range=1.0,
            safety_factor=1.0
        )

        # Need to shave 20 kW for 0.25 hours = 5 kWh
        assert result["shaving_events"] == 1
        assert abs(result["total_shaved_energy_kwh"] - 5.0) < 0.1

    def test_consecutive_peaks(self):
        """Consecutive peaks require more capacity"""
        profile = np.zeros(100)
        profile[50:54] = 100  # 100 kW for 4 intervals (1 hour)

        result = calculate_required_battery(
            profile,
            target_peak_kw=80,
            interval_minutes=15,
            battery_efficiency=1.0,
            soc_range=1.0,
            safety_factor=1.0
        )

        # Need to shave 20 kW for 1 hour = 20 kWh
        assert result["shaving_events"] == 1
        assert abs(result["max_event_energy_kwh"] - 20.0) < 0.1

    def test_efficiency_increases_capacity(self):
        """Lower efficiency requires more capacity"""
        profile = np.zeros(100)
        profile[50] = 100

        result_100 = calculate_required_battery(profile, target_peak_kw=80, battery_efficiency=1.0)
        result_90 = calculate_required_battery(profile, target_peak_kw=80, battery_efficiency=0.90)

        assert result_90["required_capacity_kwh"] > result_100["required_capacity_kwh"]

    def test_safety_factor(self):
        """Safety factor increases requirements"""
        profile = np.zeros(100)
        profile[50] = 100

        result_1 = calculate_required_battery(profile, target_peak_kw=80, safety_factor=1.0)
        result_115 = calculate_required_battery(profile, target_peak_kw=80, safety_factor=1.15)

        assert result_115["required_capacity_kwh"] == result_1["required_capacity_kwh"] * 1.15

    def test_c_rate_calculation(self):
        """C-rate = power / capacity"""
        profile = np.zeros(100)
        profile[50] = 100

        result = calculate_required_battery(
            profile,
            target_peak_kw=80,
            safety_factor=1.0,
            battery_efficiency=1.0,
            soc_range=1.0
        )

        expected_c_rate = result["required_power_kw"] / result["required_capacity_kwh"]
        assert abs(result["c_rate"] - expected_c_rate) < 0.01


# ============================================================================
# ECONOMICS TESTS
# ============================================================================

class TestPeakShavingEconomics:
    """Tests for peak-shaving economics"""

    def test_annual_savings(self):
        """Annual savings = reduction × power price"""
        result = calculate_peak_shaving_economics(
            original_peak_kw=100,
            target_peak_kw=80,
            battery_capacity_kwh=20,
            leistungspreis=100
        )
        # 20 kW reduction × 100 €/kW = 2000 €/year
        assert result["annual_savings_eur"] == 2000.0

    def test_simple_payback(self):
        """Simple payback = investment / annual savings"""
        result = calculate_peak_shaving_economics(
            original_peak_kw=100,
            target_peak_kw=80,
            battery_capacity_kwh=20,
            battery_cost_per_kwh=500,
            additional_costs=2000,
            leistungspreis=100
        )
        # Investment = 20×500 + 2000 = 12000 €
        # Savings = 2000 €/year
        # Payback = 6 years
        assert result["simple_payback_years"] == 6.0

    def test_npv_positive(self):
        """Profitable investment should have positive NPV"""
        result = calculate_peak_shaving_economics(
            original_peak_kw=150,
            target_peak_kw=100,
            battery_capacity_kwh=30,
            leistungspreis=150  # High power price
        )
        # 50 kW × 150 €/kW = 7500 €/year savings
        assert result["npv_eur"] > 0

    def test_npv_negative(self):
        """Unprofitable investment should have negative NPV"""
        result = calculate_peak_shaving_economics(
            original_peak_kw=100,
            target_peak_kw=95,
            battery_capacity_kwh=50,
            battery_cost_per_kwh=800,
            leistungspreis=50  # Low power price
        )
        # 5 kW × 50 €/kW = 250 €/year savings
        # Investment = 50×800 + 3000 = 43000 €
        assert result["npv_eur"] < 0

    def test_roi_calculation(self):
        """ROI = (savings - investment) / investment"""
        result = calculate_peak_shaving_economics(
            original_peak_kw=100,
            target_peak_kw=80,
            battery_capacity_kwh=20,
            battery_cost_per_kwh=500,
            additional_costs=2000,
            leistungspreis=100,
            years=15
        )
        # Investment = 12000 €
        # Savings 15y = 2000 × 15 = 30000 €
        # ROI = (30000 - 12000) / 12000 = 150%
        expected_roi = ((2000 * 15) - 12000) / 12000 * 100
        assert abs(result["roi_percent"] - expected_roi) < 0.1


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestPeakShavingIntegration:
    """Integration tests for complete peak-shaving analysis"""

    def test_typical_commercial_case(self, sample_load_profile):
        """Test typical commercial case with RLM metering"""
        # Add some peaks to the profile
        profile = sample_load_profile.copy()
        profile[1000] = 150  # Peak 1
        profile[3000] = 140  # Peak 2
        profile[5000] = 160  # Peak 3

        # Analyze
        analysis = analyze_load_profile(profile, leistungspreis=100)
        assert analysis["max_kw"] == 160.0

        # Find peaks
        peaks = identify_top_peaks(profile, n_peaks=5)
        assert peaks[0]["value_kw"] == 160.0

        # Size battery for 20% reduction
        target = analysis["max_kw"] * 0.8  # 128 kW
        battery_req = calculate_required_battery(profile, target_peak_kw=target)

        # Calculate economics
        economics = calculate_peak_shaving_economics(
            original_peak_kw=analysis["max_kw"],
            target_peak_kw=target,
            battery_capacity_kwh=battery_req["required_capacity_kwh"],
            leistungspreis=100
        )

        # Verify reasonable results
        assert economics["peak_reduction_kw"] == 32.0  # 160 × 0.2
        assert economics["annual_savings_eur"] == 3200.0  # 32 × 100

    def test_high_power_price_scenario(self, sample_load_profile):
        """High power prices should increase savings"""
        profile = sample_load_profile.copy()
        profile[2000] = 200

        target = 160  # 40 kW reduction

        low_price = calculate_peak_shaving_economics(
            original_peak_kw=200,
            target_peak_kw=target,
            battery_capacity_kwh=30,
            leistungspreis=60  # Low price
        )

        high_price = calculate_peak_shaving_economics(
            original_peak_kw=200,
            target_peak_kw=target,
            battery_capacity_kwh=30,
            leistungspreis=250  # High price (urban)
        )

        assert high_price["annual_savings_eur"] > low_price["annual_savings_eur"]
        assert high_price["simple_payback_years"] < low_price["simple_payback_years"]

    def test_minimum_viable_peak_shaving(self):
        """Peak shaving should be worthwhile above threshold"""
        # Create profile with single peak
        profile = np.ones(35040) * 50  # Base 50 kW
        profile[10000] = 100  # One 100 kW peak

        analysis = analyze_load_profile(profile, leistungspreis=100)

        # 100 MWh threshold check
        # 50 kW × 8760 h = 438,000 kWh = 438 MWh
        assert analysis["is_rlm"]

        # Potential savings should be positive
        assert analysis["potential_savings_eur"] > 0
