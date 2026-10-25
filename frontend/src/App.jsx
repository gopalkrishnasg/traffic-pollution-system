import React, { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import PredictPage from "./pages/PredictPage.jsx";
import CorrelationPage from "./pages/CorrelationPage.jsx";
import RoutePage from "./pages/RoutePage.jsx";
import HistoryPage from "./pages/HistoryPage.jsx";
import { fetchHealth, fetchDashboardSummary } from "./api/client.js";

export default function App() {
  const [health, setHealth] = useState(null);
  const [isSyntheticActive, setIsSyntheticActive] = useState(true);

  useEffect(() => {
    fetchHealth()
      .then((h) => setHealth(h))
      .catch(() => setHealth({ status: "offline" }));

    fetchDashboardSummary()
      .then((s) => {
        if (s?.dataset_status) {
          setIsSyntheticActive(Boolean(s.dataset_status.is_synthetic));
        }
      })
      .catch(() => {});
  }, []);

  return (
    <div className="app-shell">
      <Navbar healthStatus={health} isSyntheticActive={isSyntheticActive} />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/predict" element={<PredictPage />} />
          <Route
            path="/correlations"
            element={<CorrelationPage onDatasetChange={setIsSyntheticActive} />}
          />
          <Route path="/routes" element={<RoutePage />} />
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </main>
    </div>
  );
}