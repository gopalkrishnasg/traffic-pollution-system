from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from app.config import settings
from app.ml.preprocessing import clean_and_align_dataset, CANDIDATE_FEATURES

BENGALURU_CORRIDORS = [
    {"name": "Silk Board Junction", "lat": 12.9177, "lon": 77.6238, "base_traffic": 4200},
    {"name": "Majestic / Kempegowda", "lat": 12.9767, "lon": 77.5713, "base_traffic": 3600},
    {"name": "Whitefield ITPL", "lat": 12.9850, "lon": 77.7369, "base_traffic": 3400},
    {"name": "Hebbal Flyover", "lat": 13.0358, "lon": 77.5970, "base_traffic": 3900},
    {"name": "Electronic City Phase 1", "lat": 12.8452, "lon": 77.6602, "base_traffic": 3100},
]


def generate_synthetic_bengaluru_dataset(
    output_path: Path | None = None, num_days: int = 18, seed: int = 42
) -> Path:
    """
    Generate a reproducible synthetic dataset representing hourly observations across
    5 Bengaluru corridors. Explicitly tagged with is_synthetic=True.
    """
    target_path = output_path or settings.SYNTHETIC_CSV_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)
    start_ts = pd.Timestamp("2026-09-01 00:00:00")
    hours = num_days * 24
    records = []

    for corridor in BENGALURU_CORRIDORS:
        prev_pm25 = 38.0
        for h in range(hours):
            ts = start_ts + pd.Timedelta(hours=h)
            hour = ts.hour
            day_of_week = ts.dayofweek
            is_weekend = 1 if day_of_week >= 5 else 0

            # Diurnal traffic wave: morning peak (8-11), evening peak (17-21)
            morning_peak = np.exp(-0.5 * ((hour - 9.0) / 1.8) ** 2)
            evening_peak = np.exp(-0.5 * ((hour - 18.5) / 2.2) ** 2)
            weekend_factor = 0.72 if is_weekend else 1.0

            traffic_vol = (
                corridor["base_traffic"]
                * weekend_factor
                * (0.22 + 0.85 * morning_peak + 0.95 * evening_peak)
                + rng.normal(0, 180)
            )
            traffic_vol = float(np.clip(traffic_vol, 250.0, 6500.0))

            # Speed inversely related to traffic density
            free_flow_speed = 54.0
            traffic_speed = (
                free_flow_speed * (1.0 - 0.68 * (traffic_vol / 6500.0))
                + rng.normal(0, 3.2)
            )
            traffic_speed = float(np.clip(traffic_speed, 8.0, 65.0))

            if traffic_speed < 20:
                congestion = "HIGH"
            elif traffic_speed < 35:
                congestion = "MODERATE"
            else:
                congestion = "LOW"

            # Weather variables for Bengaluru (~20C to 32C)
            diurnal_temp = np.sin((hour - 6) * np.pi / 12.0)
            temperature = float(np.clip(25.5 + 4.8 * diurnal_temp + rng.normal(0, 0.9), 17.0, 36.0))
            relative_humidity = float(
                np.clip(68.0 - 18.0 * diurnal_temp + rng.normal(0, 4.5), 28.0, 96.0)
            )
            wind_speed = float(np.clip(11.0 + 4.0 * diurnal_temp + rng.normal(0, 2.5), 1.5, 32.0))
            precip_prob = rng.random()
            precipitation = float(
                np.round(rng.exponential(2.4), 2) if precip_prob > 0.88 else 0.0
            )

            # Pollutant dynamics (synthetic demonstration formula with autocorrelation)
            emission_pressure = (traffic_vol / 1000.0) * 7.8 + max(0.0, (30.0 - traffic_speed) * 0.65)
            dispersion_factor = 1.0 / (1.0 + 0.045 * wind_speed + 0.12 * precipitation)
            pm2_5 = (
                0.35 * prev_pm25
                + 0.65 * (18.0 + emission_pressure * dispersion_factor)
                + rng.normal(0, 3.5)
            )
            pm2_5 = float(np.clip(pm2_5, 8.0, 240.0))
            prev_pm25 = pm2_5

            pm10 = float(
                np.clip(
                    pm2_5 * 1.65 + (traffic_vol / 1000.0) * 5.2 - 1.8 * precipitation + rng.normal(0, 6.0),
                    15.0,
                    420.0,
                )
            )
            no2 = float(
                np.clip(
                    12.0 + (traffic_vol / 1000.0) * 9.5 - 0.5 * wind_speed + rng.normal(0, 3.0),
                    5.0,
                    180.0,
                )
            )
            o3 = float(
                np.clip(22.0 + max(0.0, diurnal_temp) * 24.0 + rng.normal(0, 4.0), 8.0, 140.0)
            )
            co = float(
                np.clip(280.0 + (traffic_vol / 1000.0) * 145.0 + rng.normal(0, 35.0), 150.0, 2500.0)
            )

            # US-EPA inspired piecewise approximation from PM2.5 + PM10 + NO2
            if pm2_5 <= 12.0:
                aqi_pm25 = (50.0 / 12.0) * pm2_5
            elif pm2_5 <= 35.4:
                aqi_pm25 = 50.0 + ((100.0 - 50.0) / (35.4 - 12.0)) * (pm2_5 - 12.0)
            elif pm2_5 <= 55.4:
                aqi_pm25 = 100.0 + ((150.0 - 100.0) / (55.4 - 35.4)) * (pm2_5 - 35.4)
            else:
                aqi_pm25 = 150.0 + ((200.0 - 150.0) / (150.4 - 55.4)) * (pm2_5 - 55.4)

            aqi_pm10 = (100.0 / 154.0) * pm10
            aqi_no2 = (100.0 / 188.0) * no2
            composite_aqi = float(
                np.clip(max(aqi_pm25, aqi_pm10, aqi_no2) + rng.normal(0, 2.0), 12.0, 320.0)
            )

            records.append(
                {
                    "timestamp": ts.isoformat(),
                    "location_name": corridor["name"],
                    "latitude": corridor["lat"],
                    "longitude": corridor["lon"],
                    "traffic_volume": round(traffic_vol, 1),
                    "traffic_speed": round(traffic_speed, 1),
                    "congestion_level": congestion,
                    "temperature": round(temperature, 1),
                    "relative_humidity": round(relative_humidity, 1),
                    "wind_speed": round(wind_speed, 1),
                    "precipitation": round(precipitation, 2),
                    "pm2_5": round(pm2_5, 1),
                    "pm10": round(pm10, 1),
                    "no2": round(no2, 1),
                    "o3": round(o3, 1),
                    "co": round(co, 1),
                    "aqi": round(composite_aqi, 1),
                    "data_origin": "SYNTHETIC_BENGALURU_SEED_42",
                }
            )

    df = pd.DataFrame(records)
    df.to_csv(target_path, index=False)
    return target_path


def load_active_dataset() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Load the active dataset or generate the synthetic demonstration dataset if none exists."""
    active_path = settings.ACTIVE_CSV_PATH
    if not active_path.exists():
        generate_synthetic_bengaluru_dataset(settings.SYNTHETIC_CSV_PATH)
        active_path = settings.SYNTHETIC_CSV_PATH

    raw_df = pd.read_csv(active_path)
    cleaned_df, cleaning_notes = clean_and_align_dataset(raw_df)

    is_synthetic = True
    if "data_origin" in cleaned_df.columns:
        origins = cleaned_df["data_origin"].astype(str).unique().tolist()
        is_synthetic = any("SYNTHETIC" in o.upper() for o in origins)
    elif active_path.name != settings.SYNTHETIC_CSV_PATH.name:
        is_synthetic = False

    available_features = [c for c in CANDIDATE_FEATURES if c in cleaned_df.columns]

    metadata = {
        "dataset_name": active_path.name,
        "dataset_path": str(active_path),
        "is_synthetic": is_synthetic,
        "row_count": len(cleaned_df),
        "available_features": available_features,
        "has_target_aqi": "aqi" in cleaned_df.columns,
        "cleaning_notes": cleaning_notes,
    }
    return cleaned_df, metadata