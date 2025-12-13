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

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
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
    const response = await client.get(`/projects/${projectId}/simulations`);
    return response.data;
  },

  // ============ OFFERS ============
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
};

export default api;
export { client };
