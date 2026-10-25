import time
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
import httpx
from app.config import settings

_WEATHER_CACHE: Dict[Tuple[float, float], Tuple[float, Dict[str, Any]]] = {}


def fetch_weather_data(latitude: float, longitude: float) -> Dict[str, Any]:
    key = (round(latitude, 3), round(longitude, 3))
    now = time.time()

    if key in _WEATHER_CACHE:
        ts, cached_payload = _WEATHER_CACHE[key]
        if now - ts < settings.CACHE_TTL_SECONDS:
            result = dict(cached_payload)
            result["is_cached"] = True
            return result

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
        "timezone": "auto",
    }

    try:
        with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
            resp = client.get(settings.OPEN_METEO_WEATHER_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        current = data.get("current", {})
        payload = {
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": current.get("time", datetime.now(timezone.utc).isoformat()),
            "temperature": current.get("temperature_2m"),
            "relative_humidity": current.get("relative_humidity_2m"),
            "wind_speed": current.get("wind_speed_10m"),
            "precipitation": current.get("precipitation"),
            "source": "OPEN_METEO_WEATHER_API_LIVE",
            "is_cached": False,
            "is_fallback": False,
            "warning": None,
        }
        _WEATHER_CACHE[key] = (now, payload)
        return payload

    except Exception as exc:
        if key in _WEATHER_CACHE:
            _, stale_payload = _WEATHER_CACHE[key]
            stale_copy = dict(stale_payload)
            stale_copy["is_cached"] = True
            stale_copy["warning"] = f"Live weather request failed ({exc}); serving cached observation."
            return stale_copy

        return {
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "temperature": 26.5,
            "relative_humidity": 62.0,
            "wind_speed": 11.5,
            "precipitation": 0.0,
            "source": "FALLBACK_DEMO_WEATHER_BENGALURU",
            "is_cached": False,
            "is_fallback": True,
            "warning": (
                f"Open-Meteo Weather API unreachable ({type(exc).__name__}). "
                "Displaying explicitly labeled demonstration fallback values."
            ),
        }
