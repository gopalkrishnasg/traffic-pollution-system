import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchDashboardSummary, fetchFeatureImportance } from "../api/client.js";
import SummaryCard from "../components/SummaryCard.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { TrendLineChart, FeatureImportanceChart } from "../components/Charts.jsx";

const BENGALURU_PRESETS = [
  { label: "Central Bengaluru (MG Road / Cubbon Park)", lat: 12.9716, lon: 77.5946 },
  { label: "Silk Board Junction", lat: 12.9177, lon: 77.6238 },
  { label: "Whitefield ITPL", lat: 12.985, lon: 77.7369 },
  { label: "Hebbal Flyover", lat: 13.0358, lon: 77.597 },
  { label: "Electronic City Phase 1", lat: 12.8452, lon: 77.6602 }
];

export default function Dashboard() {
  const [selectedLoc, setSelectedLoc] = useState(BENGALURU_PRESETS[0]);
  const [summary, setSummary] = useState(null);
  const [importances, setImportances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = async (loc) => {
    setLoading(true);
    setError(null);
    try {
      const [sumData, impData] = await Promise.all([
        fetchDashboardSummary(loc.lat, loc.lon),
        fetchFeatureImportance()
      ]);
      setSummary(sumData);
      setImportances(impData.importances || []);
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          "Unable to connect to the FastAPI backend. Ensure uvicorn is running on port 8000."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(selectedLoc);
  }, [selectedLoc]);

  if (loading) {
    return <div className="loading-panel">Loading Bengaluru Environmental & Traffic Intelligence...</div>;
  }

  if (error) {
    return (
      <div className="error-panel">
        <h3>Backend Connection Error</h3>
        <p>{error}</p>
        <button className="btn-primary" onClick={() => loadData(selectedLoc)}>
          Retry Connection
        </button>
      </div>
    );
  }

  const aq = summary.observed_air_quality;
  const pred = summary.predicted_snapshot;
  const weather = summary.weather;
  const traffic = summary.traffic;
  const metrics = summary.model_metrics;

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h2>Environmental & Traffic Overview Dashboard</h2>
          <p>
            Comparing observed regional background air quality with Random Forest corridor
            predictions in Bengaluru.
          </p>
        </div>
        <div className="header-controls">
          <select
            className="select-input"
            value={selectedLoc.label}
            onChange={(e) => {
              const found = BENGALURU_PRESETS.find((p) => p.label === e.target.value);
              if (found) setSelectedLoc(found);
            }}
          >
            {BENGALURU_PRESETS.map((p) => (
              <option key={p.label} value={p.label}>
                {p.label}
              </option>
            ))}
          </select>
          <Link to="/routes" className="btn-primary">
            Compare Eco Routes →
          </Link>
        </div>
      </header>

      {(aq.warning || weather.warning) && (
        <div className="warning-banner">
          <strong>External API Notice:</strong> {aq.warning || weather.warning}
        </div>
      )}

      <div className="summary-grid">
        <SummaryCard
          title="Observed Background AQI (US)"
          primaryValue={aq.us_aqi ?? "N/A"}
          unit="US AQI"
          subtitle={`EU AQI: ${aq.european_aqi ?? "N/A"} | PM2.5: ${aq.pm2_5 ?? "N/A"} µg/m³`}
          badgeText={aq.is_fallback ? "FALLBACK DEMO" : "OPEN-METEO LIVE"}
          badgeType={aq.is_fallback ? "warn" : "success"}
          accentColor="#0ea5e9"
        >
          <small>Timestamp: {aq.timestamp}</small>
        </SummaryCard>

        <SummaryCard
          title="RF Predicted Corridor AQI"
          primaryValue={pred.predicted_aqi}
          unit="US AQI"
          subtitle={`Category: ${pred.category}`}
          badgeText="MODEL ESTIMATE"
          badgeType="info"
          accentColor={pred.color}
        >
          <small>Model: {pred.model_version}</small>
        </SummaryCard>

        <SummaryCard
          title="Meteorological Conditions"
          primaryValue={weather.temperature ?? "N/A"}
          unit="°C"
          subtitle={`Humidity: ${weather.relative_humidity ?? "N/A"}% | Wind: ${
            weather.wind_speed ?? "N/A"
          } km/h`}
          badgeText={weather.is_fallback ? "FALLBACK DEMO" : "OPEN-METEO LIVE"}
          badgeType={weather.is_fallback ? "warn" : "success"}
          accentColor="#f59e0b"
        >
          <small>Precipitation: {weather.precipitation ?? 0} mm</small>
        </SummaryCard>

        <SummaryCard
          title="Corridor Traffic State"
          primaryValue={traffic.traffic_volume}
          unit="veh/h"
          subtitle={`Avg Speed: ${traffic.traffic_speed} km/h (${traffic.congestion_level})`}
          badgeText="SYNTHETIC DIURNAL"
          badgeType="warn"
          accentColor="#8b5cf6"
        >
          <small>{traffic.note}</small>
        </SummaryCard>
      </div>

      <div className="two-col-grid">
        <div className="panel-card">
          <div className="panel-card-header">
            <h3>Active Dataset Trend (AQI, PM2.5 & Traffic Volume)</h3>
            <StatusBadge
              text={
                summary.dataset_status.is_synthetic
                  ? "SYNTHETIC DATASET"
                  : "HISTORICAL CSV"
              }
              type={summary.dataset_status.is_synthetic ? "warn" : "success"}
            />
          </div>
          <TrendLineChart data={summary.historical_trend} />
        </div>

        <div className="panel-card">
          <div className="panel-card-header">
            <h3>Random Forest Feature Importance</h3>
            <StatusBadge
              text={`R² = ${metrics.r2} | MAE = ${metrics.mae}`}
              type="info"
            />
          </div>
          <FeatureImportanceChart items={importances} />
          <p className="muted-note">
            Evaluated on {metrics.test_samples} chronological test observations (
            {metrics.is_synthetic_dataset ? "Synthetic Seed=42" : "Uploaded CSV"}).
          </p>
        </div>
      </div>

      <div className="panel-card">
        <div className="panel-card-header">
          <h3>Recent AQI Predictions Logged in SQLite</h3>
          <Link to="/history" className="link-btn">
            View Full Audit Log →
          </Link>
        </div>
        {summary.recent_predictions.length === 0 ? (
          <p className="empty-box">
            No manual predictions recorded yet. Visit the AQI Prediction Lab to run a test.
          </p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Timestamp (UTC)</th>
                <th>Location</th>
                <th>Predicted AQI</th>
                <th>Category</th>
                <th>Data Provenance</th>
              </tr>
            </thead>
            <tbody>
              {summary.recent_predictions.map((item) => (
                <tr key={item.id}>
                  <td>#{item.id}</td>
                  <td>{new Date(item.created_at).toLocaleString()}</td>
                  <td>{item.location_label}</td>
                  <td>
                    <strong>{item.predicted_aqi}</strong>
                  </td>
                  <td>{item.aqi_category}</td>
                  <td>
                    <StatusBadge
                      text={item.is_synthetic ? "SYNTHETIC / HYBRID" : "USER / LIVE"}
                      type={item.is_synthetic ? "warn" : "success"}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}