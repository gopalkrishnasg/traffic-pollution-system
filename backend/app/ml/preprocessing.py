from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

# Canonical column names supported across datasets
CANONICAL_COLUMNS = {
    "timestamp": ["timestamp", "date", "datetime", "time", "recorded_at"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lon", "lng"],
    "traffic_volume": ["traffic_volume", "volume", "vehicle_count", "vehicles_per_hour"],
    "traffic_speed": ["traffic_speed", "avg_speed", "speed_kmh", "speed"],
    "congestion_level": ["congestion_level", "congestion"],
    "temperature": ["temperature", "temp", "temp_c", "temperature_2m"],
    "relative_humidity": ["relative_humidity", "humidity", "rh", "relative_humidity_2m"],
    "wind_speed": ["wind_speed", "wind", "wind_speed_10m"],
    "precipitation": ["precipitation", "rain", "rainfall"],
    "pm2_5": ["pm2_5", "pm2.5", "pm25"],
    "pm10": ["pm10", "pm_10"],
    "no2": ["no2", "nitrogen_dioxide"],
    "o3": ["o3", "ozone"],
    "co": ["co", "carbon_monoxide"],
    "aqi": ["aqi", "us_aqi", "air_quality_index"],
}

CANDIDATE_FEATURES = [
    "traffic_volume",
    "traffic_speed",
    "temperature",
    "relative_humidity",
    "wind_speed",
    "precipitation",
    "pm2_5",
    "pm10",
    "no2",
    "o3",
    "co",
]


def standardize_columns(df: pd.DataFrame, custom_mapping: Dict[str, str] | None = None) -> pd.DataFrame:
    """Map dataset columns to canonical names safely without inventing data."""
    df_copy = df.copy()
    lower_to_orig = {col.strip().lower(): col for col in df_copy.columns}
    rename_map = {}

    if custom_mapping:
        for canonical, user_col in custom_mapping.items():
            if user_col in df_copy.columns:
                rename_map[user_col] = canonical

    for canonical, aliases in CANONICAL_COLUMNS.items():
        if canonical in rename_map.values():
            continue
        for alias in aliases:
            if alias.lower() in lower_to_orig:
                orig_col = lower_to_orig[alias.lower()]
                rename_map[orig_col] = canonical
                break

    return df_copy.rename(columns=rename_map)


def clean_and_align_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Validate, deduplicate, sort chronologically, and clean dataset.
    Does not fabricate missing traffic or pollutant columns.
    """
    notes: List[str] = []
    df = standardize_columns(df)

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        invalid_ts = int(df["timestamp"].isna().sum())
        if invalid_ts > 0:
            notes.append(f"Dropped {invalid_ts} rows with unparseable timestamps.")
            df = df.dropna(subset=["timestamp"])

        subset_cols = ["timestamp"]
        if "location_name" in df.columns:
            subset_cols.append("location_name")
        elif "latitude" in df.columns and "longitude" in df.columns:
            subset_cols.extend(["latitude", "longitude"])

        before_dedup = len(df)
        df = df.drop_duplicates(subset=subset_cols, keep="first")
        dups_removed = before_dedup - len(df)
        if dups_removed > 0:
            notes.append(f"Removed {dups_removed} duplicate timestamp/coordinate rows.")

        df = df.sort_values("timestamp").reset_index(drop=True)

    numeric_cols = [c for c in CANDIDATE_FEATURES + ["aqi"] if c in df.columns]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        # Remove physically impossible negative values for concentrations/traffic
        if col != "temperature":
            neg_mask = df[col] < 0
            neg_count = int(neg_mask.sum())
            if neg_count > 0:
                df.loc[neg_mask, col] = np.nan
                notes.append(f"Replaced {neg_count} negative values in '{col}' with NaN.")

    return df, notes


def map_aqi_category(aqi_value: float, standard: str = "US_AQI") -> Dict[str, str]:
    """Return AQI category label, color hex, and non-medical guidance note."""
    val = float(aqi_value)
    if standard == "EU_AQI":
        if val <= 20:
            return {
                "category": "Good (EU)",
                "color": "#10b981",
                "note": "Model estimate indicates low air pollution under European index scale.",
            }
        if val <= 40:
            return {
                "category": "Fair (EU)",
                "color": "#84cc16",
                "note": "Model estimate indicates fair air quality under European index scale.",
            }
        if val <= 60:
            return {
                "category": "Moderate (EU)",
                "color": "#f59e0b",
                "note": "Model estimate indicates moderate pollution levels.",
            }
        if val <= 80:
            return {
                "category": "Poor (EU)",
                "color": "#f97316",
                "note": "Model estimate indicates elevated pollution; consider reducing prolonged roadside exposure.",
            }
        if val <= 100:
            return {
                "category": "Very Poor (EU)",
                "color": "#ef4444",
                "note": "Model estimate indicates high pollution concentration along the evaluated area.",
            }
        return {
            "category": "Extremely Poor (EU)",
            "color": "#7f1d1d",
            "note": "Model estimate indicates severe pollution levels.",
        }

    # Default US EPA AQI breakpoints
    if val <= 50:
        return {
            "category": "Good",
            "color": "#10b981",
            "note": "Estimated US AQI (0-50): Minimal estimated air pollution impact.",
        }
    if val <= 100:
        return {
            "category": "Moderate",
            "color": "#eab308",
            "note": "Estimated US AQI (51-100): Acceptable estimated air quality; minor concern for sensitive groups.",
        }
    if val <= 150:
        return {
            "category": "Unhealthy for Sensitive Groups",
            "color": "#f97316",
            "note": "Estimated US AQI (101-150): Elevated estimated particulates/gases near traffic corridors.",
        }
    if val <= 200:
        return {
            "category": "Unhealthy",
            "color": "#ef4444",
            "note": "Estimated US AQI (151-200): High estimated pollution; eco-friendly routing recommended.",
        }
    if val <= 300:
        return {
            "category": "Very Unhealthy",
            "color": "#8b5cf6",
            "note": "Estimated US AQI (201-300): Very high estimated pollution exposure.",
        }
    return {
        "category": "Hazardous",
        "color": "#7f1d1d",
        "note": "Estimated US AQI (>300): Severe estimated air pollution levels.",
    }