import React, { useEffect, useState } from "react";
import { fetchPredictionHistory } from "../api/client.js";
import StatusBadge from "../components/StatusBadge.jsx";

export default function HistoryPage() {
  const [records, setRecords] = useState([]);
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPredictionHistory(100);
      setRecords(data);
      if (data.length > 0) setSelectedRecord(data[0]);
    } catch (err) {
      setError("Failed to load SQLite prediction history.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  if (loading) {
    return <div className="loading-panel">Loading SQLite Prediction History...</div>;
  }

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h2>SQLite Prediction History & Provenance Log</h2>
          <p>
            Every AQI prediction is persisted locally with its input feature vector, model
            version, and synthetic/live data provenance tag.
          </p>
        </div>
        <button className="btn-secondary" onClick={loadHistory}>
          Refresh Log
        </button>
      </header>

      {error && <div className="error-panel">{error}</div>}

      <div className="two-col-grid">
        <div className="panel-card">
          <h3>Stored Records ({records.length})</h3>
          {records.length === 0 ? (
            <div className="empty-box">No predictions saved yet.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Timestamp</th>
                  <th>Location</th>
                  <th>AQI</th>
                  <th>Category</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr
                    key={r.id}
                    className={selectedRecord?.id === r.id ? "selected-row" : ""}
                  >
                    <td>#{r.id}</td>
                    <td>{new Date(r.created_at).toLocaleString()}</td>
                    <td>{r.location_label}</td>
                    <td>
                      <strong>{r.predicted_aqi}</strong>
                    </td>
                    <td>{r.aqi_category}</td>
                    <td>
                      <button
                        className="btn-small"
                        onClick={() => setSelectedRecord(r)}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="panel-card">
          <h3>Record Feature Snapshot</h3>
          {!selectedRecord ? (
            <div className="empty-box">Select a prediction row to inspect its details.</div>
          ) : (
            <div>
              <div className="mini-metrics-row">
                <div>
                  <strong>Record ID:</strong> #{selectedRecord.id}
                </div>
                <div>
                  <strong>Scale:</strong> {selectedRecord.aqi_standard}
                </div>
                <div>
                  <strong>Mode:</strong> {selectedRecord.prediction_mode}
                </div>
              </div>
              <p className="small-meta">
                <strong>Coordinates:</strong> ({selectedRecord.latitude},{" "}
                {selectedRecord.longitude})
              </p>
              <p className="small-meta">
                <strong>Model Version:</strong> {selectedRecord.model_version}
              </p>
              <p className="small-meta">
                <strong>Data Source:</strong> {selectedRecord.data_source}
              </p>
              <div style={{ margin: "10px 0" }}>
                <StatusBadge
                  text={
                    selectedRecord.is_synthetic
                      ? "SYNTHETIC / HYBRID DATA INVOLVED"
                      : "USER / REAL OBSERVATION"
                  }
                  type={selectedRecord.is_synthetic ? "warn" : "success"}
                />
              </div>
              <h4>Serialized Feature Inputs</h4>
              <div className="feature-tags-grid">
                {Object.entries(selectedRecord.input_features || {}).map(([k, v]) => (
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