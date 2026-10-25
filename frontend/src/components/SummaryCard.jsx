import React from "react";
import StatusBadge from "./StatusBadge.jsx";

export default function SummaryCard({
  title,
  primaryValue,
  unit,
  subtitle,
  badgeText,
  badgeType = "info",
  accentColor,
  children
}) {
  return (
    <div
      className="summary-card"
      style={accentColor ? { borderTop: `4px solid ${accentColor}` } : undefined}
    >
      <div className="summary-card-header">
        <h3>{title}</h3>
        {badgeText && <StatusBadge text={badgeText} type={badgeType} />}
      </div>
      <div className="summary-card-value">
        <span className="val">{primaryValue}</span>
        {unit && <span className="unit">{unit}</span>}
      </div>
      {subtitle && <p className="summary-card-sub">{subtitle}</p>}
      {children && <div className="summary-card-extra">{children}</div>}
    </div>
  );
}