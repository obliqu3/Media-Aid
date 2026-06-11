// Axios API client with Firebase auth token injection
import axios from "axios";
import { getIdToken } from "./firebase";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  timeout: 30000,
});

// Inject Firebase ID token on every request
api.interceptors.request.use(async (config) => {
  const token = await getIdToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Handle auth errors globally
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// ── API helpers ──────────────────────────────────────────────────

export const vitalsAPI = {
  log: (data) => api.post("/vitals", data),
  list: (limit = 30) => api.get(`/vitals?limit=${limit}`),
  latest: () => api.get("/vitals/latest"),
  summary: () => api.get("/vitals/summary"),
};

export const aiAPI = {
  chat: (content, sessionId) => api.post("/ai/chat", { content, session_id: sessionId }),
  riskAssessment: (data) => api.post("/ai/risk-assessment", data),
};

export const medicationsAPI = {
  list: () => api.get("/medications"),
  add: (data) => api.post("/medications", data),
  remove: (id) => api.delete(`/medications/${id}`),
  adherence: () => api.get("/medications/adherence"),
};

export const healthAPI = {
  getProfile: () => api.get("/health/profile"),
  updateProfile: (data) => api.put("/health/profile", data),
};

export const reportsAPI = {
  list: () => api.get("/reports"),
  generate: (period) => api.get(`/reports/generate?period=${period}`, { responseType: "blob" }),
};

export const clinicsAPI = {
  nearby: (lat, lon, radius = 5000) =>
    api.get(`/clinics/nearby?lat=${lat}&lon=${lon}&radius=${radius}`),
};

export default api;
