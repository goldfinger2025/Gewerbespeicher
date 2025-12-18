import axios, { AxiosInstance, AxiosError } from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Create axios instance
const client: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

// Request interceptor - Add JWT token
client.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - Handle errors
client.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      if (typeof window !== "undefined") {
        localStorage.removeItem("access_token");
        window.location.href = "/auth/login";
      }
    }
    return Promise.reject(error);
  }
);

// API Methods
const api = {
  // ============ AUTHENTICATION ============
  login: async (email: string, password: string) => {
    const response = await client.post("/auth/login", { email, password });
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", response.data.access_token);
    }
    return response.data;
  },

  register: async (data: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    company_name?: string;
  }) => {
    const response = await client.post("/auth/register", data);
    return response.data;
  },

  logout: async () => {
    try {
      // Call server to invalidate token (add to blacklist)
      await client.post("/auth/logout", {});
    } catch {
      // Ignore errors - we're logging out anyway
    } finally {
      // Always remove local token
      if (typeof window !== "undefined") {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      }
    }
  },

  // ============ PROJECTS ============
  getProjects: async (params?: { skip?: number; limit?: number; status?: string }) => {
    const response = await client.get("/projects", { params });
    return response.data;
  },

  getProject: async (id: string) => {
    const response = await client.get(`/projects/${id}`);
    return response.data;
  },

  createProject: async (data: {
    customer_name: string;
    customer_email?: string;
    address: string;
    postal_code: string;
    city?: string;
    project_name?: string;
    pv_peak_power_kw: number;
    battery_capacity_kwh: number;
    battery_power_kw?: number;
    annual_consumption_kwh: number;
    electricity_price_eur_kwh?: number;
  }) => {
    const response = await client.post("/projects", data);
    return response.data;
  },

  updateProject: async (id: string, data: Partial<any>) => {
    const response = await client.patch(`/projects/${id}`, data);
    return response.data;
  },

  deleteProject: async (id: string) => {
    const response = await client.delete(`/projects/${id}`);
    return response.data;
  },

  // ============ SIMULATIONS ============
  simulate: async (projectId: string, options?: { simulation_type?: string }) => {
    const response = await client.post("/simulations", {
      project_id: projectId,
      ...options,
    });
    return response.data;
  },

  getSimulation: async (id: string) => {
    const response = await client.get(`/simulations/${id}`);
    return response.data;
  },

  getProjectSimulations: async (projectId: string) => {
    const response = await client.get(`/simulations/project/${projectId}`);
    return response.data;
  },

  // ============ OFFERS ============
  getOffers: async (params?: { skip?: number; limit?: number; status?: string }) => {
    const response = await client.get("/offers", { params });
    return response.data;
  },

  createOffer: async (simulationId: string, options?: { generate_pdf?: boolean }) => {
    const response = await client.post("/offers", {
      simulation_id: simulationId,
      generate_pdf: options?.generate_pdf ?? true,
    });
    return response.data;
  },

  getOffer: async (id: string) => {
    const response = await client.get(`/offers/${id}`);
    return response.data;
  },

  getOfferPdf: async (id: string) => {
    const response = await client.get(`/offers/${id}/pdf`, {
      responseType: 'blob',
    });
    return response.data;
  },

  getOfferPreview: async (id: string) => {
    const response = await client.get(`/offers/${id}/preview`);
    return response.data;
  },

  getSignatureLink: async (offerId: string) => {
    const response = await client.get(`/offers/${offerId}/signature-link`);
    return response.data;
  },

  sendOffer: async (offerId: string, data: { customer_email: string; message?: string }) => {
    const response = await client.put(`/offers/${offerId}/send`, data);
    return response.data;
  },

  // ============ COMPONENTS ============
  getComponents: async (params?: {
    category?: string;
    manufacturer?: string;
    min_price?: number;
    max_price?: number;
  }) => {
    const response = await client.get("/components", { params });
    return response.data;
  },

  getComponent: async (id: string) => {
    const response = await client.get(`/components/${id}`);
    return response.data;
  },

  // ============ OPTIMIZATION ============
  optimize: async (
    projectId: string,
    options?: {
      optimization_target?: "max-roi" | "max-autonomy" | "min-cost";
      constraints?: Record<string, any>;
    }
  ) => {
    const response = await client.post("/ai/optimize", {
      project_id: projectId,
      ...options,
    });
    return response.data;
  },

  dimensionSystem: async (
    projectId: string,
    constraints?: {
      max_budget?: number;
      max_roof_area?: number;
      min_autonomy?: number;
    }
  ) => {
    const response = await client.post("/ai/dimension", {
      project_id: projectId,
      constraints: constraints || null,
    });
    return response.data;
  },

  compareScenarios: async (projectId: string) => {
    const response = await client.get(`/ai/compare/${projectId}`);
    return response.data;
  },

  getComponentRecommendations: async (projectId: string, budgetEur?: number) => {
    const response = await client.post("/ai/recommend-components", null, {
      params: { project_id: projectId, budget_eur: budgetEur },
    });
    return response.data;
  },

  getProjectFaq: async (projectId: string) => {
    const response = await client.get(`/ai/faq/${projectId}`);
    return response.data;
  },

  // ============ ANALYTICS ============
  getDashboardMetrics: async (period?: "week" | "month" | "year") => {
    const response = await client.get("/analytics/dashboard", {
      params: { period },
    });
    return response.data;
  },

  // ============ HEALTH CHECK ============
  healthCheck: async () => {
    const response = await client.get("/health");
    return response.data;
  },

  // ============ GEWERBESPEICHER ============

  // Peak-Shaving
  analyzePeakShaving: async (data: {
    load_profile_kw: number[];
    battery_capacity_kwh: number;
    battery_power_kw: number;
    leistungspreis_eur_kw?: number;
    leistungspreis_kategorie?: "niedrig" | "mittel" | "hoch" | "sehr_hoch" | "extrem";
    interval_minutes?: number;
  }) => {
    const response = await client.post("/gewerbe/peak-shaving/analyze", data);
    return response.data;
  },

  calculatePeakShavingEconomics: async (data: {
    original_peak_kw: number;
    target_peak_kw: number;
    battery_capacity_kwh: number;
    battery_power_kw: number;
    leistungspreis_eur_kw?: number;
    battery_cost_per_kwh?: number;
  }) => {
    const response = await client.post("/gewerbe/peak-shaving/economics", data);
    return response.data;
  },

  getLeistungspreise: async () => {
    const response = await client.get("/gewerbe/peak-shaving/leistungspreise");
    return response.data;
  },

  // Compliance
  generateComplianceChecklist: async (data: {
    pv_kwp: number;
    battery_kwh: number;
    battery_power_kw: number;
    jahresverbrauch_kwh: number;
    bundesland?: string;
    inbetriebnahme_datum?: string;
    eeg_typ?: "teileinspeisung" | "volleinspeisung";
  }) => {
    const response = await client.post("/gewerbe/compliance/checklist", data);
    return response.data;
  },

  getPara14aInfo: async (battery_power_kw: number) => {
    const response = await client.get("/gewerbe/compliance/para-14a", {
      params: { battery_power_kw },
    });
    return response.data;
  },

  getMastrInfo: async () => {
    const response = await client.get("/gewerbe/compliance/mastr");
    return response.data;
  },

  // EEG & Tarife
  getEegVerguetung: async (pv_kwp: number, eeg_typ?: string) => {
    const response = await client.get("/gewerbe/eeg/verguetung", {
      params: { pv_kwp, eeg_typ },
    });
    return response.data;
  },

  getEegTarife: async () => {
    const response = await client.get("/gewerbe/eeg/tarife");
    return response.data;
  },

  // Förderung
  getFoerderungUebersicht: async () => {
    const response = await client.get("/gewerbe/foerderung/uebersicht");
    return response.data;
  },

  getLandesfoerderung: async (bundesland: string) => {
    const response = await client.get(`/gewerbe/foerderung/bundesland/${bundesland}`);
    return response.data;
  },

  // Kosten
  calculateInvestmentCosts: async (data: {
    pv_kwp: number;
    battery_kwh: number;
    include_installation?: boolean;
  }) => {
    const response = await client.post("/gewerbe/kosten/investition", data);
    return response.data;
  },

  getCostReference: async () => {
    const response = await client.get("/gewerbe/kosten/referenz");
    return response.data;
  },

  // Notstrom (Emergency Power)
  analyzeEmergencyPower: async (data: {
    critical_loads_kw: number[];
    battery_capacity_kwh: number;
    battery_power_kw: number;
    required_backup_hours: number;
    pv_kwp?: number;
    load_profile_kw?: number[];
  }) => {
    const response = await client.post("/gewerbe/notstrom/analyze", data);
    return response.data;
  },

  simulateBlackout: async (data: {
    load_profile_kw: number[];
    battery_capacity_kwh: number;
    battery_power_kw: number;
    critical_loads_kw: number;
    pv_profile_kw?: number[];
    outage_start_hour: number;
    outage_duration_hours: number;
    initial_soc?: number;
  }) => {
    const response = await client.post("/gewerbe/notstrom/simulate-blackout", data);
    return response.data;
  },

  getNotstromInfo: async () => {
    const response = await client.get("/gewerbe/notstrom/info");
    return response.data;
  },

  // Netzentgelte (Grid Fees)
  getNetzentgeltByPlz: async (plz: string) => {
    const response = await client.get(`/gewerbe/netzentgelt/plz/${plz}`);
    return response.data;
  },

  getNetzentgeltByNetzbetreiber: async (netzbetreiber_id: string) => {
    const response = await client.get(`/gewerbe/netzentgelt/netzbetreiber/${netzbetreiber_id}`);
    return response.data;
  },
};

export default api;
export { client };
