// Simulation Types
export interface Simulation {
  id: string;
  project_id: string;

  // Parameters
  simulation_type: SimulationType;
  time_resolution: TimeResolution;

  // Annual Results
  pv_generation_kwh: number;
  consumed_from_grid_kwh: number;
  self_consumed_kwh: number;
  fed_to_grid_kwh: number;
  battery_discharge_cycles: number;

  // Key Metrics
  autonomy_degree_percent: number;
  self_consumption_ratio_percent: number;
  pv_coverage_percent: number;

  // Betriebsstunden und Volllaststunden
  battery_charging_hours?: number;
  battery_discharging_hours?: number;
  battery_operating_hours?: number;
  battery_full_load_hours?: number;
  battery_utilization_percent?: number;
  battery_capacity_factor_percent?: number;
  pv_full_load_hours?: number;

  // Financial Results (30-year horizon)
  annual_savings_eur: number;
  total_savings_eur: number;
  payback_period_years: number;
  npv_eur?: number;
  irr_percent?: number;
  total_investment_eur?: number;

  // Detailed Data
  hourly_data?: HourlyDataPoint[];
  monthly_summary?: MonthlySummary[];

  // Status
  is_latest: boolean;
  status: SimulationStatus;

  created_at: string;
}

export type SimulationType = 'standard' | 'peak-shaving' | 'arbitrage';

export type TimeResolution = 'hourly' | 'daily' | 'yearly';

export type SimulationStatus = 'pending' | 'running' | 'completed' | 'failed';

// Hourly Data Point
export interface HourlyDataPoint {
  timestamp: string;
  pv_generation: number;        // kWh
  consumption: number;          // kWh
  battery_soc: number;          // kWh (State of Charge)
  battery_charge: number;       // kWh
  battery_discharge: number;    // kWh
  grid_import: number;          // kWh
  grid_export: number;          // kWh
}

// Monthly Summary
export interface MonthlySummary {
  month: number;  // 1-12
  pv_generation_kwh: number;
  consumption_kwh: number;
  self_consumption_kwh: number;
  grid_import_kwh: number;
  grid_export_kwh: number;
  autonomy_percent?: number;
  savings_eur?: number;
}

// Simulation Request
export interface SimulationRequest {
  project_id: string;
  simulation_type?: SimulationType;
  run_async?: boolean;
}

// Simulation Response (matches backend SimulationResponse)
export interface SimulationResponse {
  id: string;
  project_id: string;
  simulation_type: string;
  status: SimulationStatus;
  results?: SimulationKPIs;
  monthly_summary?: MonthlySummary[];
  created_at: string;
}

// KPI Summary for Dashboard
export interface SimulationKPIs {
  autonomy_degree_percent: number;
  annual_savings_eur: number;
  payback_period_years: number;
  self_consumption_ratio_percent: number;
  pv_generation_kwh: number;
  battery_cycles: number;
  // Neue Kennzahlen: Betriebsstunden und Volllaststunden
  battery_charging_hours?: number;
  battery_discharging_hours?: number;
  battery_operating_hours?: number;
  battery_full_load_hours?: number;
  battery_utilization_percent?: number;
  battery_capacity_factor_percent?: number;
  pv_full_load_hours?: number;
}

// Phase 2: Scenario Comparison Types
export interface ScenarioData {
  name: string;
  description: string;
  pv_kw: number;
  battery_kwh: number;
  investment_eur: number;
  autonomy_percent: number;
  annual_savings_eur: number;
  payback_years: number;
  npv_20y_eur: number;
  co2_savings_tons: number;
  highlight: string;
}

export interface ComparisonResult {
  scenarios: ScenarioData[];
  recommendation: string;
  comparison_summary: string;
}

// Phase 2: Dimensioning Types
export interface DimensioningConstraints {
  max_budget?: number;
  max_roof_area?: number;
  min_autonomy?: number;
}

export interface ExpectedResults {
  autonomy_percent: number;
  self_consumption_percent: number;
  annual_savings_eur: number;
  payback_years: number;
  co2_savings_tons: number;
}

export interface Investment {
  pv_cost_eur: number;
  battery_cost_eur: number;
  installation_cost_eur: number;
  total_cost_eur: number;
}

export interface DimensioningFactors {
  pv_to_consumption_ratio: number;
  battery_to_pv_ratio: number;
  specific_yield_kwh_per_kwp: number;
}

export interface DimensioningResult {
  recommended_pv_kw: number;
  recommended_battery_kwh: number;
  recommended_battery_power_kw: number;
  expected_results: ExpectedResults;
  investment: Investment;
  dimensioning_factors: DimensioningFactors;
  reasoning: string;
  recommendations: string[];
}

// Phase 2: Detailed Offer Text
export interface DetailedOfferText {
  greeting: string;
  executive_summary: string;
  system_description: string;
  economic_benefits: string;
  environmental_benefits: string;
  next_steps: string;
  closing: string;
}
