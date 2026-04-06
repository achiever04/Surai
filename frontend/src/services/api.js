import axios from 'axios';

const API_BASE_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1`;

const api = axios.create({
  baseURL: API_BASE_URL,
  // Axios will automatically set the correct Content-Type (JSON vs Form Data) based on the payload.
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor: auto-logout on 401/403 ──────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const status = error.response.status;

      if (status === 401 || status === 403) {
        // Token expired or invalid — clear session and redirect to login
        const currentPath = window.location.pathname;
        if (currentPath !== '/login') {
          console.warn(`Received ${status} — session expired, redirecting to login.`);
          sessionStorage.removeItem('access_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

// API endpoints
export const authAPI = {
  // Ensure we can pass config overrides if needed
  login: (credentials) => api.post('/auth/login', credentials),
  logout: () => api.post('/auth/logout'),
  getCurrentUser: () => api.get('/auth/me'),
};

export const cameraAPI = {
  getAll: () => api.get('/cameras'),
  getById: (id) => api.get(`/cameras/${id}`),
  create: (data) => api.post('/cameras', data),
  update: (id, data) => api.put(`/cameras/${id}`, data),
  delete: (id) => api.delete(`/cameras/${id}`),
  getStream: (id) => `${API_BASE_URL}/cameras/${id}/stream`,
  // Start camera with AI detection
  start: (id) => api.post(`/cameras/${id}/start`),
  // Stop camera and release resources
  stop: (id) => api.post(`/cameras/${id}/stop`),
};

export const detectionAPI = {
  getAll: (params) => api.get('/detections', { params }),
  getById: (id) => api.get(`/detections/${id}`),
  updateStatus: (id, status) => api.patch(`/detections/${id}/status`, { status }),
  update: (id, data) => api.patch(`/detections/${id}`, data),
  delete: (id) => api.delete(`/detections/${id}`),
  bulkDelete: (ids) => api.post('/detections/bulk-delete', { ids }),
  verify: (id) => api.patch(`/detections/${id}`, { is_verified: true, operator_action: 'verified' }),
  reject: (id) => api.patch(`/detections/${id}`, { is_false_positive: true, operator_action: 'rejected' }),
};

export const watchlistAPI = {
  getAll: () => api.get('/watchlist'),
  getById: (id) => api.get(`/watchlist/${id}`),
  // Explicitly allow FormData for file uploads
  create: (formData) => api.post('/watchlist', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  update: (id, data) => api.put(`/watchlist/${id}`, data),
  delete: (id) => api.delete(`/watchlist/${id}`),
};

export const blockchainAPI = {
  getEvidence: (eventId) => api.get(`/blockchain/evidence/${eventId}`),
  verifyIntegrity: (eventId) => api.post(`/blockchain/verify/${eventId}`),
  getTransactions: (params) => api.get('/blockchain/transactions', { params }),
};

export const analyticsAPI = {
  getDashboardStats: () => api.get('/analytics/dashboard'),
  getDetectionTrends: (params) => api.get('/analytics/trends', { params }),
  getCameraHealth: () => api.get('/analytics/camera-health'),
};

export const alertsAPI = {
  getAll: (params) => api.get('/alerts', { params }),
  getSummary: (params) => api.get('/alerts/summary', { params }),
};

// Health check API (for dashboard system health)
export const systemAPI = {
  getHealth: () => axios.get(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/health`),
};

// Settings & Configuration API
export const settingsAPI = {
  /** GET /api/v1/settings — fetch current persisted config */
  get: () => api.get('/settings'),
  /** POST /api/v1/settings/update — save new config values */
  update: (payload) => api.post('/settings/update', payload),
};


export default api;