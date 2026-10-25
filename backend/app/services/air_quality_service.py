import time
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
import httpx
from app.config import settings

_AQ_CACHE: Dict[Tuple[float, float], Tuple[float, Dict[str, Any]]] = {}


def fetch_air_quality_data(latitude: float, longitude: float) -> Dict[str, Any]:
    key = (round(latitude, 3), round(longitude, 3))
    now = time.time()

    if key in _AQ_CACHE:
        ts, cached_payload = _AQ_CACHE[key]
        if now - ts < settings.CACHE_TTL_SECONDS:
            result = dict(cached_payload)
            result["is_cached"] = True
            return result

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone,european_aqi,us_aqi",
        "timezone": "auto",
    }

    try:
        with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
            resp = client.get(settings.OPEN_METEO_AQ_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        current = data.get("current", {})
        payload = {
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": current.get("time", datetime.now(timezone.utc).isoformat()),
            "pm2_5": current.get("pm2_5"),
            "pm10": current.get("pm10"),
            "no2": current.get("nitrogen_dioxide"),
            "o3": current.get("ozone"),
            "co": current.get("carbon_monoxide"),
            "us_aqi": current.get("us_aqi"),
            "european_aqi": current.get("european_aqi"),
            "aqi_standard_reported": "US_AQI (with EU_AQI also retrieved)",
            "source": "OPEN_METEO_AIR_QUALITY_API_LIVE",
            "is_cached": False,
            "is_fallback": False,
            "warning": None,
        }
        _AQ_CACHE[key] = (now, payload)
        return payload

    except Exception as exc:
        if key in _AQ_CACHE:
            _, stale_payload = _AQ_CACHE[key]
            stale_copy = dict(stale_payload)
            stale_copy["is_cached"] = True
            stale_copy["warning"] = f"Live AQ request failed ({exc}); serving cached observation."
            return stale_copy

        return {
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pm2_5": 34.2,
            "pm10": 68.5,
            "no2": 28.4,
            "o3": 44.0,
            "co": 520.0,
            "us_aqi": 97.0,
            "european_aqi": 48.0,
            "aqi_standard_reported": "US_AQI",
            "source": "FALLBACK_DEMO_AIR_QUALITY_BENGALURU",
            "is_cached": False,
            "is_fallback": True,
            "warning": (
                f"Open-Meteo Air Quality API unreachable ({type(exc).__name__}). "
                "Using clearly labeled demonstration fallback values."
            ),
        }
