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
  
  // Financial Results (30-year horizon)
  annual_savings_eur: number;
  total_savings_eur: number;
  payback_period_years: number;
  npv_eur?: number;
  irr_percent?: number;
  
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
  savings_eur: number;
}

// Simulation Request
export interface SimulationRequest {
  project_id: string;
  simulation_type?: SimulationType;
  run_async?: boolean;
}

// Simulation Response
export interface SimulationResponse {
  simulation_id: string;
  status: SimulationStatus;
  results?: Simulation;
}

// KPI Summary for Dashboard
export interface SimulationKPIs {
  autonomy_degree_percent: number;
  annual_savings_eur: number;
  payback_period_years: number;
  self_consumption_ratio_percent: number;
  pv_generation_kwh: number;
  battery_cycles: number;
}
