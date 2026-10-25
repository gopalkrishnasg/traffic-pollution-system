import React from "react";

export default function StatusBadge({ text, type = "info" }) {
  return <span className={`badge badge-${type}`}>{text}</span>;
}