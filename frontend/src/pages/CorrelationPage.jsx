import React, { useEffect, useState } from "react";
import {
  fetchCorrelations,
  uploadDatasetCsv,
  resetSyntheticDataset,
  retrainModel
} from "../api/client.js";
import StatusBadge from "../components/StatusBadge.jsx";
import { VariableScatterChart, CorrelationHeatmap } from "../components/Charts.jsx";

export default function CorrelationPage({ onDatasetChange }) {
  const [corrData, setCorrData] = useState(null);
  const [selectedScatterVar, setSelectedScatterVar] = useState("traffic_volume");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const loadCorrelations = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCorrelations();
      setCorrData(data);
      if (onDatasetChange) onDatasetChange(data.is_synthetic);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load correlation analysis.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCorrelations();
  }, []);

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setMessage(null);
    setError(null);
    try {
      const res = await uploadDatasetCsv(file);
      setMessage(
        `${res.message} (MAE: ${res.metrics.mae}, RMSE: ${res.metrics.rmse}, R²: ${res.metrics.r2})`
      );
      await loadCorrelations();
    } catch (err) {
      setError(err?.response?.data?.detail || "CSV upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleResetSynthetic = async () => {
    setUploading(true);
    setMessage(null);
    setError(null);
    try {
      const res = await resetSyntheticDataset();
      setMessage(res.message);
      await loadCorrelations();
    } catch (err) {
      setError("Failed to reset synthetic dataset.");
    } finally {
      setUploading(false);
    }
  };

  const handleRetrainTrafficWeatherOnly = async () => {
    setUploading(true);
    setMessage(null);
    setError(null);
    try {
      const res = await retrainModel(true);
      setMessage(
        `Retrained model using Traffic + Weather features only (${res.model_version}): MAE=${res.mae}, R²=${res.r2}`
      );
    } catch (err) {
      setError("Retraining failed.");
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return <div className="loading-panel">Computing Pearson & Spearman Correlations...</div>;
  }

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h2>Traffic, Weather & Pollutant Correlation Analysis</h2>
          <p>
            Active Dataset: <strong>{corrData?.dataset_name}</strong> ({corrData?.total_rows}{" "}
            rows) — Statistical association does not imply physical causation.
          </p>
        </div>
        <div className="header-controls">
          <label className="btn-secondary file-label">
            {uploading ? "Processing..." : "Upload Custom CSV"}
            <input
              type="file"
              accept=".csv"
              onChange={handleFileUpload}
              disabled={uploading}
              hidden
            />
          </label>
          <button
            className="btn-secondary"
            onClick={handleRetrainTrafficWeatherOnly}
            disabled={uploading}
          >
            Train Weather+Traffic Only
          </button>
          <button
            className="btn-primary"
            onClick={handleResetSynthetic}
            disabled={uploading}
          >
            Reset to Synthetic Demo Data
          </button>
        </div>
      </header>

      {message && <div className="success-banner">{message}</div>}
      {error && <div className="error-panel">{error}</div>}

      {corrData?.warnings?.map((w, idx) => (
        <div key={idx} className="warning-banner">
          {w}
        </div>
      ))}

      <div className="two-col-grid">
        <div className="panel-card">
          <div className="panel-card-header">
            <h3>Pearson Correlation Heatmap</h3>
            <StatusBadge
              text={corrData?.is_synthetic ? "SYNTHETIC SEED=42" : "UPLOADED CSV"}
              type={corrData?.is_synthetic ? "warn" : "success"}
            />
          </div>
          <CorrelationHeatmap
            variables={corrData?.matrix_variables}
            matrix={corrData?.pearson_matrix}
          />
        </div>

        <div className="panel-card">
          <div className="panel-card-header">
            <h3>Interactive Variable vs. AQI Scatter Plot</h3>
            <select
              className="select-input"
              value={selectedScatterVar}
              onChange={(e) => setSelectedScatterVar(e.target.value)}
            >
              {corrData?.correlations.map((c) => (
                <option key={c.variable} value={c.variable}>
                  {c.variable}
                </option>
              ))}
            </select>
          </div>
          <VariableScatterChart
            samples={corrData?.scatter_samples}
            xKey={selectedScatterVar}
            xLabel={selectedScatterVar}
          />
        </div>
      </div>

      <div className="panel-card">
        <h3>Detailed Correlation Coefficients & Cautious Interpretations</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Variable</th>
              <th>Pearson (r)</th>
              <th>Spearman (ρ)</th>
              <th>Valid Samples</th>
              <th>Missing</th>
              <th>Analytical Interpretation</th>
            </tr>
          </thead>
          <tbody>
            {corrData?.correlations.map((c) => (
              <tr key={c.variable}>
                <td>
                  <strong>{c.variable}</strong>
                </td>
                <td>{c.pearson_r !== null ? c.pearson_r.toFixed(3) : "N/A"}</td>
                <td>{c.spearman_rho !== null ? c.spearman_rho.toFixed(3) : "N/A"}</td>
                <td>{c.sample_count}</td>
                <td>{c.missing_count}</td>
                <td>{c.interpretation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}