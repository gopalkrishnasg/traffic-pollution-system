from typing import Dict, Any, List
import numpy as np
import httpx
from app.config import settings


def _generate_fallback_routes(
    origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float
) -> List[Dict[str, Any]]:
    lat1, lon1, lat2, lon2 = map(np.radians, [origin_lat, origin_lon, dest_lat, dest_lon])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    straight_km = float(6371.0 * (2 * np.arcsin(np.sqrt(a))))
    base_road_km = max(1.2, straight_km * 1.28)

    steps = 12
    r1_coords = []
    for i in range(steps + 1):
        t = i / steps
        lat = origin_lat + t * (dest_lat - origin_lat)
        lon = origin_lon + t * (dest_lon - origin_lon)
        r1_coords.append([round(float(lat), 5), round(float(lon), 5)])

    r2_coords = []
    perp_lat = -(dest_lon - origin_lon) * 0.22
    perp_lon = (dest_lat - origin_lat) * 0.22
    for i in range(steps + 1):
        t = i / steps
        arc = np.sin(np.pi * t)
        lat = origin_lat + t * (dest_lat - origin_lat) + arc * perp_lat
        lon = origin_lon + t * (dest_lon - origin_lon) + arc * perp_lon
        r2_coords.append([round(float(lat), 5), round(float(lon), 5)])

    return [
        {
            "route_id": "route_1",
            "route_name": "Primary Arterial Corridor (Demo Geometry)",
            "distance_km": round(base_road_km, 2),
            "duration_min": round((base_road_km / 28.0) * 60.0, 1),
            "geometry": r1_coords,
        },
        {
            "route_id": "route_2",
            "route_name": "Outer Ring Bypass Alternative (Demo Geometry)",
            "distance_km": round(base_road_km * 1.14, 2),
            "duration_min": round(((base_road_km * 1.14) / 30.5) * 60.0, 1),
            "geometry": r2_coords,
        },
    ]


def fetch_candidate_routes(
    origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float
) -> Dict[str, Any]:
    coords_str = f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
    url = f"{settings.OSRM_BASE_URL}/route/v1/driving/{coords_str}"
    params = {
        "alternatives": "true",
        "overview": "full",
        "geometries": "geojson",
    }

    try:
        with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        osrm_routes = data.get("routes", [])
        if not osrm_routes:
            raise ValueError("OSRM returned zero routes.")

        parsed_routes = []
        for idx, r in enumerate(osrm_routes[:3]):
            coords_lon_lat = r.get("geometry", {}).get("coordinates", [])
            geometry_lat_lon = [[float(c[1]), float(c[0])] for c in coords_lon_lat]
            dist_km = round(float(r.get("distance", 1000.0)) / 1000.0, 2)
            dur_min = round(float(r.get("duration", 600.0)) / 60.0, 1)

            parsed_routes.append(
                {
                    "route_id": f"route_{idx + 1}",
                    "route_name": (
                        "OSRM Primary Route" if idx == 0 else f"OSRM Alternative Route {idx + 1}"
                    ),
                    "distance_km": max(0.2, dist_km),
                    "duration_min": max(1.0, dur_min),
                    "geometry": geometry_lat_lon,
                }
            )

        warnings = []
        if len(parsed_routes) == 1:
            fallback_pair = _generate_fallback_routes(
                origin_lat, origin_lon, dest_lat, dest_lon
            )
            alt = fallback_pair[1]
            alt["route_id"] = "route_2"
            alt["route_name"] = "Secondary Bypass Corridor (Synthesized Detour)"
            alt["distance_km"] = round(parsed_routes[0]["distance_km"] * 1.12, 2)
            alt["duration_min"] = round(parsed_routes[0]["duration_min"] * 1.10, 1)
            parsed_routes.append(alt)
            warnings.append(
                "OSRM returned only 1 road geometry for this pair; a labeled secondary detour "
                "corridor was added to allow comparative route scoring."
            )

        return {
            "routing_source": "OSRM_PUBLIC_API (Baseline Road Duration - Not Live Congestion)",
            "is_fallback_routing": False,
            "routes": parsed_routes,
            "warnings": warnings,
        }

    except Exception as exc:
        fallback_routes = _generate_fallback_routes(
            origin_lat, origin_lon, dest_lat, dest_lon
        )
        return {
            "routing_source": "DEMONSTRATION_GEOMETRIC_ROUTING_FALLBACK",
            "is_fallback_routing": True,
            "routes": fallback_routes,
            "warnings": [
                f"OSRM routing service unavailable ({type(exc).__name__}). "
                "Using clearly labeled demonstration route geometries."
            ],
        }
