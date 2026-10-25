import React, { useState, useEffect } from "react";
import { compareRoutes } from "../api/client.js";
import MapView from "../components/MapView.jsx";
import StatusBadge from "../components/StatusBadge.jsx";

const BENGALURU_LANDMARKS = [
  { label: "Silk Board Junction", lat: 12.9177, lon: 77.6238 },
  { label: "Whitefield ITPL", lat: 12.985, lon: 77.7369 },
  { label: "Majestic Bus Stand", lat: 12.9767, lon: 77.5713 },
  { label: "Hebbal Flyover", lat: 13.0358, lon: 77.597 },
  { label: "Electronic City Phase 1", lat: 12.8452, lon: 77.6602 },
  { label: "Indiranagar 100ft Road", lat: 12.9784, lon: 77.6408 }
];

export default function RoutePage() {
  const [origin, setOrigin] = useState(BENGALURU_LANDMARKS[0]);
  const [destination, setDestination] = useState(BENGALURU_LANDMARKS[1]);
  const [activePinMode, setActivePinMode] = useState("origin");
  const [durationWeight, setDurationWeight] = useState(0.35);
  const [exposureWeight, setExposureWeight] = useState(0.65);
  const [maxDetourRatio, setMaxDetourRatio] = useState(1.45);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runComparison = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await compareRoutes({
        origin_lat: Number(origin.lat),
        origin_lon: Number(origin.lon),
        origin_label: origin.label,
        destination_lat: Number(destination.lat),
        destination_lon: Number(destination.lon),
        destination_label: destination.label,
        duration_weight: Number(durationWeight),
        exposure_weight: Number(exposureWeight),
        max_detour_ratio: Number(maxDetourRatio)
      });
      setComparison(res);
    } catch (err) {
      setError(err?.response?.data?.detail || "Route comparison failed.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runComparison();
  }, []);

  const handleMapClick = (lat, lon, mode) => {
    if (mode === "origin") {
      setOrigin({
        label: `Custom Origin (${lat.toFixed(3)}, ${lon.toFixed(3)})`,
        lat,
        lon
      });
    } else {
      setDestination({
        label: `Custom Destination (${lat.toFixed(3)}, ${lon.toFixed(3)})`,
        lat,
        lon
      });
    }
  };

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h2>Eco-Friendly vs. Fastest Route Recommendation System</h2>
          <p>
            Click anywhere on the Bengaluru map or choose landmarks to compare travel duration
            against time-integrated AQI exposure proxies.
          </p>
        </div>
        <button className="btn-primary" onClick={runComparison} disabled={loading}>
          {loading ? "Sampling Corridor AQI..." : "Recalculate Routes"}
        </button>
      </header>

      {error && <div className="error-panel">{error}</div>}

      <div className="route-controls-bar panel-card">
        <div className="route-control-col">
          <label>Origin Landmark</label>
          <select
            className="select-input"
            value={origin.label}
            onChange={(e) => {
              const found = BENGALURU_LANDMARKS.find((l) => l.label === e.target.value);
              if (found) setOrigin(found);
            }}
          >
            {BENGALURU_LANDMARKS.map((l) => (
              <option key={l.label} value={l.label}>
                {l.label}
              </option>
            ))}
            {!BENGALURU_LANDMARKS.some((l) => l.label === origin.label) && (
              <option value={origin.label}>{origin.label}</option>
            )}
          </select>
        </div>

        <div className="route-control-col">
          <label>Destination Landmark</label>
          <select
            className="select-input"
            value={destination.label}
            onChange={(e) => {
              const found = BENGALURU_LANDMARKS.find((l) => l.label === e.target.value);
              if (found) setDestination(found);
            }}
          >
            {BENGALURU_LANDMARKS.map((l) => (
              <option key={l.label} value={l.label}>
                {l.label}
              </option>
            ))}
            {!BENGALURU_LANDMARKS.some((l) => l.label === destination.label) && (
              <option value={destination.label}>{destination.label}</option>
            )}
          </select>
        </div>

        <div className="route-control-col">
          <label>Map Click Mode</label>
          <div className="toggle-group">
            <button
              type="button"
              className={activePinMode === "origin" ? "btn-primary" : "btn-secondary"}
              onClick={() => setActivePinMode("origin")}
            >
              Set Origin Pin
            </button>
            <button
              type="button"
              className={activePinMode === "destination" ? "btn-primary" : "btn-secondary"}
              onClick={() => setActivePinMode("destination")}
            >
              Set Dest Pin
            </button>
          </div>
        </div>

        <div className="route-control-col">
          <label>
            Weights (Duration: {durationWeight} | Exposure: {exposureWeight})
          </label>
          <input
            type="range"
            min="0.1"
            max="0.9"
            step="0.05"
            value={exposureWeight}
            onChange={(e) => {
              const expW = Number(e.target.value);
              setExposureWeight(expW);
              setDurationWeight(Number((1.0 - expW).toFixed(2)));
            }}
          />
          <small>Max Detour Ratio: {maxDetourRatio}x</small>
        </div>
      </div>

      <div className="two-col-grid">
        <div className="panel-card">
          <div className="panel-card-header">
            <h3>Interactive Corridor Map (Green = Eco, Blue = Fastest)</h3>
            {comparison && (
              <StatusBadge
                text={
                  comparison.is_fallback_routing ? "DEMO GEOMETRY" : "OSRM ROAD GEOMETRY"
                }
                type={comparison.is_fallback_routing ? "warn" : "success"}
              />
            )}
          </div>
          <MapView
            origin={origin}
            destination={destination}
            activePinMode={activePinMode}
            onMapClick={handleMapClick}
            routes={comparison?.routes || []}
            fastestRouteId={comparison?.fastest_route_id}
            ecoRouteId={comparison?.eco_route_id}
          />
        </div>

        <div className="panel-card">
          <h3>Recommendation Decision & Trade-Off Analysis</h3>
          {comparison ? (
            <>
              <div className="recommendation-highlight">
                <p>
                  <strong>Decision Explanation:</strong> {comparison.explanation}
                </p>
                <div className="mini-metrics-row">
                  <div>
                    <strong>Exposure Proxy Diff:</strong> -{comparison.exposure_reduction_pct}%
                  </div>
                  <div>
                    <strong>Time Trade-off:</strong> +{comparison.additional_time_min} min
                  </div>
                  <div>
                    <strong>Distance Diff:</strong> {comparison.distance_diff_km >= 0 ? "+" : ""}
                    {comparison.distance_diff_km} km
                  </div>
                </div>
              </div>

              <p className="muted-note">{comparison.methodology_note}</p>

              {comparison.warnings.map((w, i) => (
                <div key={i} className="warning-banner">
                  {w}
                </div>
              ))}

              <div className="route-cards-stack">
                {comparison.routes.map((r) => {
                  const isEco = r.route_id === comparison.eco_route_id;
                  const isFast = r.route_id === comparison.fastest_route_id;
                  return (
                    <div
                      key={r.route_id}
                      className={`route-item-card ${isEco ? "eco-border" : ""} ${
                        isFast ? "fast-border" : ""
                      }`}
                    >
                      <div className="route-item-header">
                        <h4>{r.route_name}</h4>
                        <div className="badge-group">
                          {isEco && <StatusBadge text="ECO-FRIENDLY CHOICE" type="success" />}
                          {isFast && <StatusBadge text="FASTEST ROUTE" type="info" />}
                        </div>
                      </div>
                      <div className="route-item-stats">
                        <span>
                          <strong>Distance:</strong> {r.distance_km} km
                        </span>
                        <span>
                          <strong>Est. Duration:</strong> {r.duration_min} min
                        </span>
                        <span>
                          <strong>Mean Corridor AQI:</strong> {r.average_aqi}
                        </span>
                        <span>
                          <strong>Mean PM2.5:</strong> {r.average_pm2_5} µg/m³
                        </span>
                        <span>
                          <strong>Exposure Proxy:</strong> {r.exposure_proxy_index}{" "}
                          {r.exposure_unit}
                        </span>
                        <span>
                          <strong>Composite Cost:</strong> {r.composite_cost}
                        </span>
                      </div>
                      <p className="small-meta">
                        {r.traffic_summary} | Confidence: {r.data_confidence}
                      </p>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="empty-box">Calculating route alternatives...</div>
          )}
        </div>
      </div>
    </div>
  );
}