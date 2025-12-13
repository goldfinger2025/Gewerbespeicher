// Project Types
export interface Project {
  id: string;
  user_id: string;
  
  // Customer Info
  customer_name: string;
  customer_email?: string;
  customer_phone?: string;
  customer_company?: string;
  
  // Location
  address: string;
  postal_code: string;
  city?: string;
  latitude?: number;
  longitude?: number;
  
  // Project Data
  project_name?: string;
  description?: string;
  status: ProjectStatus;
  
  // PV System
  pv_peak_power_kw: number;
  pv_orientation?: PVOrientation;
  pv_tilt_angle?: number;
  roof_area_sqm?: number;
  
  // Battery System
  battery_capacity_kwh: number;
  battery_power_kw?: number;
  battery_chemistry?: BatteryChemistry;
  battery_manufacturer?: string;
  
  // Consumption
  annual_consumption_kwh: number;
  peak_load_kw?: number;
  
  // Cost Parameters
  electricity_price_eur_kwh?: number;
  grid_fee_eur_kwh?: number;
  feed_in_tariff_eur_kwh?: number;
  
  // Timestamps
  created_at: string;
  updated_at: string;
}

export type ProjectStatus = 'draft' | 'active' | 'completed' | 'archived';

export type PVOrientation = 'north' | 'south' | 'east' | 'west' | 'southeast' | 'southwest';

export type BatteryChemistry = 'LFP' | 'NCA' | 'NMC';

// Create Project Input
export interface ProjectCreate {
  customer_name: string;
  customer_email?: string;
  customer_phone?: string;
  address: string;
  postal_code: string;
  city?: string;
  project_name?: string;
  pv_peak_power_kw: number;
  pv_orientation?: PVOrientation;
  pv_tilt_angle?: number;
  battery_capacity_kwh: number;
  battery_power_kw?: number;
  annual_consumption_kwh: number;
  electricity_price_eur_kwh?: number;
}

// Update Project Input
export type ProjectUpdate = Partial<ProjectCreate>;

// Project with Latest Simulation
export interface ProjectWithSimulation extends Project {
  latest_simulation?: {
    id: string;
    autonomy_degree_percent: number;
    annual_savings_eur: number;
    payback_period_years: number;
  };
}
