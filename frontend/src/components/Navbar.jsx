import React from "react";
import { NavLink } from "react-router-dom";

export default function Navbar({ healthStatus, isSyntheticActive }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-badge">AI-ENV</div>
        <div>
          <h1>EcoRoute Bengaluru</h1>
          <p>Traffic & AQI Intelligence</p>
        </div>
      </div>

      <div className="connection-box">
        <span
          className={`status-dot ${
            healthStatus?.status === "healthy" ? "online" : "offline"
          }`}
        />
        <span>
          {healthStatus?.status === "healthy"
            ? `API Online (${healthStatus.model_version || "RF"})`
            : "Backend Offline"}
        </span>
      </div>

      {isSyntheticActive && (
        <div className="synthetic-global-banner">
          SYNTHETIC DEMO DATASET ACTIVE (Seed 42)
        </div>
      )}

      <nav className="sidebar-nav">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
          1. Overview Dashboard
        </NavLink>
        <NavLink to="/predict" className={({ isActive }) => (isActive ? "active" : "")}>
          2. AQI Prediction Lab
        </NavLink>
        <NavLink to="/correlations" className={({ isActive }) => (isActive ? "active" : "")}>
          3. Correlation & Dataset
        </NavLink>
        <NavLink to="/routes" className={({ isActive }) => (isActive ? "active" : "")}>
          4. Eco-Route Planner
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => (isActive ? "active" : "")}>
          5. Prediction History
        </NavLink>
      </nav>

      <div className="sidebar-footer">
        <p>Default Demo City: Bengaluru, IN</p>
        <small>Open-Meteo + OSRM + Scikit-Learn RF</small>
      </div>
    </aside>
  );
}