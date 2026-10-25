from datetime import datetime, timezone
from typing import Dict, Any
import numpy as np


def estimate_corridor_traffic(
    latitude: float, longitude: float, hour_override: int | None = None
) -> Dict[str, Any]:
    now_dt = datetime.now(timezone.utc)
    ist_hour = hour_override if hour_override is not None else (now_dt.hour + 5) % 24

    morning_peak = np.exp(-0.5 * ((ist_hour - 9.0) / 2.0) ** 2)
    evening_peak = np.exp(-0.5 * ((ist_hour - 18.5) / 2.3) ** 2)

    dist_from_center = np.hypot(latitude - 12.955, longitude - 77.610)
    spatial_multiplier = float(np.clip(1.25 - dist_from_center * 2.2, 0.55, 1.30))

    base_volume = 3400.0 * spatial_multiplier
    traffic_volume = round(
        float(base_volume * (0.25 + 0.85 * morning_peak + 0.95 * evening_peak)), 1
    )
    traffic_speed = round(
        float(np.clip(54.0 * (1.0 - 0.65 * (traffic_volume / 6000.0)), 10.0, 58.0)), 1
    )

    if traffic_speed < 20.0:
        congestion = "HIGH"
    elif traffic_speed < 34.0:
        congestion = "MODERATE"
    else:
        congestion = "LOW"

    return {
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": now_dt.isoformat(),
        "traffic_volume": traffic_volume,
        "traffic_speed": traffic_speed,
        "congestion_level": congestion,
        "source": "SYNTHETIC_DIURNAL_TRAFFIC_SIMULATOR",
        "is_synthetic": True,
        "note": (
            "SYNTHETIC DEMO TRAFFIC: Estimated from diurnal IST time-of-day and Bengaluru "
            "corridor proximity. Not live road sensor data."
        ),
    }
