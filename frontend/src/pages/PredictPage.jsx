import React, { useState } from "react";
import {
  fetchWeather,
  fetchAirQuality,
  fetchTraffic,
  submitPrediction
} from "../api/client.js";
import StatusBadge from "../components/StatusBadge.jsx";

const PRESET_LOCATIONS = [
  { label: "Silk Board Junction", lat: 12.9177, lon: 77.6238 },
  { label: "Majestic Bus Stand", lat: 12.9767, lon: 77.5713 },
  { label: "Whitefield ITPL", lat: 12.985, lon: 77.7369 },
  { label: "Hebbal Flyover", lat: 13.0358, lon: 77.597 },
  { label: "Electronic City", lat: 12.8452, lon: 77.6602 }
];

export default function PredictPage() {
  const [form, setForm] = useState({
    location_label: "Silk Board Junction",
    latitude: 12.9177,
    longitude: 77.6238,
    prediction_mode: "HYBRID_LIVE_WEATHER_USER_TRAFFIC",
    aqi_standard: "US_AQI",
    traffic_volume: 3800,
    traffic_speed: 19.5,
    temperature: 27.0,
    relative_humidity: 60.0,
    wind_speed: 10.5,
    precipitation: 0.0,
    pm2_5: 42.0,
    pm10: 84.0,
    no2: 36.0,
    o3: 40.0,
    co: 610.0
  });

  const [fetchingEnv, setFetchingEnv] = useState(false);
  const [predicting, setPredicting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handlePresetChange = (e) => {
    const found = PRESET_LOCATIONS.find((p) => p.label === e.target.value);
    if (found) {
      setForm((prev) => ({
        ...prev,
        location_label: found.label,
        latitude: found.lat,
        longitude: found.lon
      }));
    }
  };

  const handleAutoFillOpenMeteo = async () => {
    setFetchingEnv(true);
    setError(null);
    try {
      const [w, aq, tr] = await Promise.all([
        fetchWeather(form.latitude, form.longitude),
        fetchAirQuality(form.latitude, form.longitude),
        fetchTraffic(form.latitude, form.longitude)
      ]);
      setForm((prev) => ({
        ...prev,
        temperature: w.temperature ?? prev.temperature,
        relative_humidity: w.relative_humidity ?? prev.relative_humidity,
        wind_speed: w.wind_speed ?? prev.wind_speed,
        precipitation: w.precipitation ?? prev.precipitation,
        pm2_5: aq.pm2_5 ?? prev.pm2_5,
        pm10: aq.pm10 ?? prev.pm10,
        no2: aq.no2 ?? prev.no2,
        o3: aq.o3 ?? prev.o3,
        co: aq.co ?? prev.co,
        traffic_volume: tr.traffic_volume,
        traffic_speed: tr.traffic_speed
      }));
    } catch (err) {
      setError("Failed to auto-populate from backend services.");
    } finally {
      setFetchingEnv(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setPredicting(true);
    setError(null);
    try {
      const payload = {
        ...form,
        latitude: Number(form.latitude),
        longitude: Number(form.longitude),
        traffic_volume: Number(form.traffic_volume),
        traffic_speed: Number(form.traffic_speed),
        temperature: Number(form.temperature),
        relative_humidity: Number(form.relative_humidity),
        wind_speed: Number(form.wind_speed),
        precipitation: Number(form.precipitation),
        pm2_5: Number(form.pm2_5),
        pm10: Number(form.pm10),
        no2: Number(form.no2),
        o3: Number(form.o3),
        co: Number(form.co)
      };
      const res = await submitPrediction(payload);
      setResult(res);
    } catch (err) {
      setError(err?.response?.data?.detail || "Prediction request failed.");
    } finally {
      setPredicting(false);
    }
  };

  const updateField = (key, val) => {
    setForm((prev) => ({ ...prev, [key]: val }));
  };

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h2>Random Forest AQI Prediction Lab</h2>
          <p>
            Configure location, weather, pollutant background, and corridor traffic to generate
            and log an AQI estimate.
          </p>
        </div>
        <button
          type="button"
          className="btn-secondary"
          onClick={handleAutoFillOpenMeteo}
          disabled={fetchingEnv}
        >
          {fetchingEnv
            ? "Fetching Live Open-Meteo Data..."
            : "Auto-Fill Live Weather/AQ + Synthetic Traffic"}
        </button>
      </header>

      {error && <div className="error-panel">{error}</div>}

      <div className="two-col-grid">
        <form className="panel-card form-grid" onSubmit={handleSubmit}>
          <h3>Input Parameters</h3>

          <div className="form-row">
            <label>Preset Corridor</label>
            <select
              className="select-input"
              value={form.location_label}
              onChange={handlePresetChange}
            >
              {PRESET_LOCATIONS.map((p) => (
                <option key={p.label} value={p.label}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          <div className="form-row-split">
            <div>
              <label>Latitude</label>
              <input
                type="number"
                step="0.0001"
                value={form.latitude}
                onChange={(e) => updateField("latitude", e.target.value)}
                required
              />
            </div>
            <div>
              <label>Longitude</label>
              <input
                type="number"
                step="0.0001"
                value={form.longitude}
                onChange={(e) => updateField("longitude", e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-row-split">
            <div>
              <label>Prediction Mode</label>
              <select
                value={form.prediction_mode}
                onChange={(e) => updateField("prediction_mode", e.target.value)}
              >
                <option value="HYBRID_LIVE_WEATHER_USER_TRAFFIC">
                  Hybrid (Open-Meteo + Traffic)
                </option>
                <option value="MANUAL_INPUT">Strict Manual Input</option>
                <option value="SYNTHETIC_DEMO">Synthetic Demo Mode</option>
              </select>
            </div>
            <div>
              <label>Target Index Scale</label>
              <select
                value={form.aqi_standard}
                onChange={(e) => updateField("aqi_standard", e.target.value)}
              >
                <option value="US_AQI">US EPA AQI (0-500)</option>
                <option value="EU_AQI">European AQI Scale</option>
              </select>
            </div>
          </div>

          <div className="form-row-split">
            <div>
              <label>Traffic Volume (veh/h)</label>
              <input
                type="number"
                step="10"
                value={form.traffic_volume}
                onChange={(e) => updateField("traffic_volume", e.target.value)}
                required
              />
            </div>
            <div>
              <label>Average Traffic Speed (km/h)</label>
              <input
                type="number"
                step="0.5"
                value={form.traffic_speed}
                onChange={(e) => updateField("traffic_speed", e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-row-split">
            <div>
              <label>Temperature (°C)</label>
              <input
                type="number"
                step="0.1"
                value={form.temperature}
                onChange={(e) => updateField("temperature", e.target.value)}
                required
              />
            </div>
            <div>
              <label>Relative Humidity (%)</label>
              <input
                type="number"
                step="1"
                value={form.relative_humidity}
                onChange={(e) => updateField("relative_humidity", e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-row-split">
            <div>
              <label>Wind Speed (km/h)</label>
              <input
                type="number"
                step="0.1"
                value={form.wind_speed}
                onChange={(e) => updateField("wind_speed", e.target.value)}
                required
              />
            </div>
            <div>
              <label>Precipitation (mm)</label>
              <input
                type="number"
                step="0.1"
                value={form.precipitation}
                onChange={(e) => updateField("precipitation", e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-row-split">
            <div>
              <label>PM2.5 (µg/m³)</label>
              <input
                type="number"
                step="0.1"
                value={form.pm2_5}
                onChange={(e) => updateField("pm2_5", e.target.value)}
                required
              />
            </div>
            <div>
              <label>PM10 (µg/m³)</label>
              <input
                type="number"
                step="0.1"
                value={form.pm10}
                onChange={(e) => updateField("pm10", e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-row-split">
            <div>
              <label>NO₂ (µg/m³)</label>
              <input
                type="number"
                step="0.1"
                value={form.no2}
                onChange={(e) => updateField("no2", e.target.value)}
                required
              />
            </div>
            <div>
              <label>Ozone O₃ (µg/m³)</label>
              <input
                type="number"
                step="0.1"
                value={form.o3}
                onChange={(e) => updateField("o3", e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-row">
            <label>Carbon Monoxide CO (µg/m³)</label>
            <input
              type="number"
              step="1"
              value={form.co}
              onChange={(e) => updateField("co", e.target.value)}
              required
            />
          </div>

          <button type="submit" className="btn-primary full-width" disabled={predicting}>
            {predicting ? "Computing RF Prediction..." : "Run AQI Prediction & Save to DB"}
          </button>
        </form>

        <div className="panel-card">
          <h3>Prediction Output & Model Diagnostics</h3>
          {!result ? (
            <div className="empty-box">
              Submit the parameters on the left to inspect the Random Forest prediction,
              category mapping, and provenance metadata.
            </div>
          ) : (
            <div className="prediction-result-box">
              <div
                className="aqi-hero-banner"
                style={{ borderLeft: `8px solid ${result.category_color}` }}
              >
                <div>
                  <span className="aqi-hero-label">
                    Predicted {result.aqi_standard.replace("_", " ")}
                  </span>
                  <div className="aqi-hero-number">{result.predicted_aqi}</div>
                  <span
                    className="aqi-category-pill"
                    style={{ backgroundColor: result.category_color }}
                  >
                    {result.aqi_category}
                  </span>
                </div>
                <div>
                  <StatusBadge
                    text={result.is_synthetic ? "SYNTHETIC / HYBRID" : "REAL / MANUAL"}
                    type={result.is_synthetic ? "warn" : "success"}
                  />
                  <p className="small-meta">Record ID: #{result.prediction_id}</p>
                  <p className="small-meta">Model: {result.model_version}</p>
                </div>
              </div>

              <p className="cautionary-box">{result.cautionary_note}</p>

              {result.warnings.length > 0 && (
                <div className="warning-banner">
                  <strong>Provenance & Data Warnings:</strong>
                  <ul>
                    {result.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              <h4>Model Evaluation Metrics (Held-Out Test Split)</h4>
              <div className="mini-metrics-row">
                <div>
                  <strong>MAE:</strong> {result.model_metrics.mae}
                </div>
                <div>
                  <strong>RMSE:</strong> {result.model_metrics.rmse}
                </div>
                <div>
                  <strong>R² Score:</strong> {result.model_metrics.r2}
                </div>
              </div>

              <h4>Feature Vector Supplied to Model</h4>
              <div className="feature-tags-grid">
                {Object.entries(result.used_features).map(([k, v]) => (
                  <div key={k} className="feature-tag-item">
                    <span>{k}:</span> <strong>{v}</strong>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}