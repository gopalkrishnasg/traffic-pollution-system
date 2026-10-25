import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  ScatterChart,
  Scatter
} from "recharts";

export function TrendLineChart({ data }) {
  if (!data || data.length === 0) {
    return <div className="empty-box">No historical trend records available.</div>;
  }
  return (
    <div className="chart-wrapper">
      <ResponsiveContainer width="100%" height={290}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="timestamp" tick={{ fontSize: 12 }} />
          <YAxis yAxisId="left" tick={{ fontSize: 12 }} />
          <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="aqi"
            name="Dataset AQI"
            stroke="#ef4444"
            strokeWidth={2}
            dot={false}
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="pm2_5"
            name="PM2.5 (µg/m³)"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="traffic_volume"
            name="Traffic (veh/h)"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function FeatureImportanceChart({ items }) {
  if (!items || items.length === 0) {
    return <div className="empty-box">No feature importance data available.</div>;
  }
  return (
    <div className="chart-wrapper">
      <ResponsiveContainer width="100%" height={290}>
        <BarChart data={items} layout="vertical" margin={{ left: 30 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis type="number" tick={{ fontSize: 12 }} />
          <YAxis dataKey="feature" type="category" width={110} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="importance" name="Relative Importance" fill="#0ea5e9" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function VariableScatterChart({ samples, xKey, xLabel }) {
  if (!samples || samples.length === 0) {
    return <div className="empty-box">No scatter data available.</div>;
  }
  const filtered = samples.filter(
    (d) => d[xKey] !== null && d[xKey] !== undefined && d.aqi !== null
  );
  return (
    <div className="chart-wrapper">
      <ResponsiveContainer width="100%" height={270}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            type="number"
            dataKey={xKey}
            name={xLabel}
            label={{ value: xLabel, position: "insideBottom", offset: -10, fontSize: 12 }}
          />
          <YAxis
            type="number"
            dataKey="aqi"
            name="AQI"
            label={{ value: "AQI", angle: -90, position: "insideLeft", fontSize: 12 }}
          />
          <Tooltip cursor={{ strokeDasharray: "3 3" }} />
          <Scatter name={`${xLabel} vs AQI`} data={filtered} fill="#6366f1" />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

export function CorrelationHeatmap({ variables, matrix }) {
  if (!variables || !matrix || matrix.length === 0) {
    return <div className="empty-box">Correlation matrix unavailable.</div>;
  }

  const getCellColor = (val) => {
    if (val === null || val === undefined) return "#f1f5f9";
    if (val >= 0) {
      const alpha = Math.min(0.9, Math.max(0.1, val));
      return `rgba(239, 68, 68, ${alpha})`;
    }
    const alpha = Math.min(0.9, Math.max(0.1, Math.abs(val)));
    return `rgba(59, 130, 246, ${alpha})`;
  };

  return (
    <div className="heatmap-scroll">
      <table className="heatmap-table">
        <thead>
          <tr>
            <th>Variable</th>
            {variables.map((v) => (
              <th key={v}>{v}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {variables.map((rowVar, rIdx) => (
            <tr key={rowVar}>
              <td className="heatmap-row-label">{rowVar}</td>
              {matrix[rIdx].map((val, cIdx) => (
                <td
                  key={`${rIdx}-${cIdx}`}
                  style={{
                    backgroundColor: getCellColor(val),
                    color: val !== null && Math.abs(val) > 0.55 ? "#ffffff" : "#0f172a"
                  }}
                >
                  {val !== null ? val.toFixed(2) : "N/A"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}