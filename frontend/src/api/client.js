import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json"
  }
});

export const fetchHealth = () => apiClient.get("/api/health").then((r) => r.data);
export const fetchDashboardSummary = (lat = 12.9716, lon = 77.5946) =>
  apiClient
    .get("/api/dashboard/summary", { params: { latitude: lat, longitude: lon } })
    .then((r) => r.data);

export const fetchWeather = (lat, lon) =>
  apiClient
    .get("/api/weather", { params: { latitude: lat, longitude: lon } })
    .then((r) => r.data);

export const fetchAirQuality = (lat, lon) =>
  apiClient
    .get("/api/air-quality", { params: { latitude: lat, longitude: lon } })
    .then((r) => r.data);

export const fetchTraffic = (lat, lon) =>
  apiClient
    .get("/api/traffic", { params: { latitude: lat, longitude: lon } })
    .then((r) => r.data);

export const submitPrediction = (payload) =>
  apiClient.post("/api/predict", payload).then((r) => r.data);

export const fetchModelMetrics = () =>
  apiClient.get("/api/model/metrics").then((r) => r.data);

export const fetchFeatureImportance = () =>
  apiClient.get("/api/model/feature-importance").then((r) => r.data);

export const retrainModel = (excludePollutants = false) =>
  apiClient
    .post(`/api/model/train?exclude_pollutants=${excludePollutants}`)
    .then((r) => r.data);

export const fetchCorrelations = () =>
  apiClient.get("/api/correlations").then((r) => r.data);

export const uploadDatasetCsv = (file) => {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient
    .post("/api/datasets/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" }
    })
    .then((r) => r.data);
};

export const resetSyntheticDataset = () =>
  apiClient.post("/api/datasets/reset-synthetic").then((r) => r.data);

export const compareRoutes = (payload) =>
  apiClient.post("/api/routes/compare", payload).then((r) => r.data);

export const fetchPredictionHistory = (limit = 50) =>
  apiClient.get("/api/history", { params: { limit } }).then((r) => r.data);
