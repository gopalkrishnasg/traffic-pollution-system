from datetime import datetime, timezone
from typing import Dict, Any, List
import numpy as np

from app.services.routing_service import fetch_candidate_routes
from app.services.weather_service import fetch_weather_data
from app.services.air_quality_service import fetch_air_quality_data
from app.services.traffic_service import estimate_corridor_traffic
from app.ml.predictor import model_manager


def _sample_geometry_points(geometry: List[List[float]], num_samples: int = 3) -> List[List[float]]:
    if not geometry:
        return [[12.9716, 77.5946]]
    if len(geometry) <= num_samples:
        return geometry
    indices = np.linspace(0, len(geometry) - 1, num_samples, dtype=int)
    return [geometry[i] for i in indices]


def evaluate_and_compare_routes(
    origin_lat: float,
    origin_lon: float,
    destination_lat: float,
    destination_lon: float,
    duration_weight: float = 0.35,
    exposure_weight: float = 0.65,
    max_detour_ratio: float = 1.45,
) -> Dict[str, Any]:
    routing_res = fetch_candidate_routes(origin_lat, origin_lon, destination_lat, destination_lon)
    raw_routes = routing_res["routes"]
    warnings: List[str] = list(routing_res.get("warnings", []))

    total_w = duration_weight + exposure_weight
    if total_w <= 0:
        w_dur, w_exp = 0.35, 0.65
    else:
        w_dur = round(duration_weight / total_w, 3)
        w_exp = round(exposure_weight / total_w, 3)

    mid_lat = (origin_lat + destination_lat) / 2.0
    mid_lon = (origin_lon + destination_lon) / 2.0
    weather = fetch_weather_data(mid_lat, mid_lon)
    if weather.get("warning"):
        warnings.append(weather["warning"])

    evaluated_routes: List[Dict[str, Any]] = []
    env_sources = set()

    for idx, r in enumerate(raw_routes):
        pts = _sample_geometry_points(r["geometry"], num_samples=3)
        sample_infos = []
        aqi_vals = []
        pm25_vals = []
        traffic_vols = []

        for pt_idx, (plat, plon) in enumerate(pts):
            aq = fetch_air_quality_data(plat, plon)
            env_sources.add(aq["source"])
            if aq.get("warning") and aq["warning"] not in warnings:
                warnings.append(aq["warning"])

            tr = estimate_corridor_traffic(plat, plon)
            corridor_factor = 1.0 if idx == 0 else max(0.68, 0.85 - 0.05 * idx)
            adj_traffic_vol = round(tr["traffic_volume"] * corridor_factor, 1)
            adj_traffic_speed = round(min(60.0, tr["traffic_speed"] / corridor_factor), 1)

            base_pm25 = float(aq.get("pm2_5") or 32.0)
            local_pm25 = round(base_pm25 * (0.78 + 0.28 * (adj_traffic_vol / 3500.0)), 1)
            local_pm10 = round(float(aq.get("pm10") or 65.0) * (0.80 + 0.25 * (adj_traffic_vol / 3500.0)), 1)
            local_no2 = round(float(aq.get("no2") or 26.0) * (0.75 + 0.32 * (adj_traffic_vol / 3500.0)), 1)

            pred_aqi, _, _, _, _ = model_manager.predict_aqi(
                {
                    "traffic_volume": adj_traffic_vol,
                    "traffic_speed": adj_traffic_speed,
                    "temperature": weather.get("temperature"),
                    "relative_humidity": weather.get("relative_humidity"),
                    "wind_speed": weather.get("wind_speed"),
                    "precipitation": weather.get("precipitation"),
                    "pm2_5": local_pm25,
                    "pm10": local_pm10,
                    "no2": local_no2,
                    "o3": aq.get("o3"),
                    "co": aq.get("co"),
                }
            )

            aqi_vals.append(pred_aqi)
            pm25_vals.append(local_pm25)
            traffic_vols.append(adj_traffic_vol)

            sample_infos.append(
                {
                    "latitude": round(plat, 5),
                    "longitude": round(plon, 5),
                    "estimated_aqi": pred_aqi,
                    "pm2_5": local_pm25,
                    "traffic_volume": adj_traffic_vol,
                    "source": f"{aq['source']} + RF_CORRIDOR_MODEL",
                }
            )

        avg_aqi = round(float(np.mean(aqi_vals)), 1)
        avg_pm25 = round(float(np.mean(pm25_vals)), 1)
        avg_traffic = float(np.mean(traffic_vols))
        dur_min = float(r["duration_min"])

        exposure_proxy = round(avg_aqi * (dur_min / 60.0), 2)

        if avg_traffic > 3200:
            traffic_summary = f"High Corridor Volume (~{int(avg_traffic)} veh/h - Synthetic Estimate)"
        elif avg_traffic > 2000:
            traffic_summary = f"Moderate Corridor Volume (~{int(avg_traffic)} veh/h - Synthetic Estimate)"
        else:
            traffic_summary = f"Lighter Corridor Volume (~{int(avg_traffic)} veh/h - Synthetic Estimate)"

        is_fallback_env = any("FALLBACK" in s for s in env_sources)
        confidence = (
            "MEDIUM (Regional Open-Meteo AQ + Synthetic Corridor Traffic)"
            if not is_fallback_env
            else "LOW (Offline Fallback Demo Mode)"
        )

        evaluated_routes.append(
            {
                "route_id": r["route_id"],
                "route_name": r["route_name"],
                "distance_km": r["distance_km"],
                "duration_min": dur_min,
                "average_aqi": avg_aqi,
                "average_pm2_5": avg_pm25,
                "exposure_proxy_index": exposure_proxy,
                "exposure_unit": "AQI-hours (Proxy Index)",
                "normalized_duration_score": 0.0,
                "normalized_exposure_score": 0.0,
                "composite_cost": 0.0,
                "traffic_summary": traffic_summary,
                "traffic_is_synthetic": True,
                "environmental_source": ", ".join(sorted(env_sources)),
                "data_confidence": confidence,
                "geometry": r["geometry"],
                "sample_points": sample_infos,
            }
        )

    durs = [er["duration_min"] for er in evaluated_routes]
    exps = [er["exposure_proxy_index"] for er in evaluated_routes]
    min_dur, max_dur = min(durs), max(durs)
    min_exp, max_exp = min(exps), max(exps)

    for er in evaluated_routes:
        norm_d = (
            (er["duration_min"] - min_dur) / (max_dur - min_dur)
            if (max_dur - min_dur) > 1e-6
            else 0.0
        )
        norm_e = (
            (er["exposure_proxy_index"] - min_exp) / (max_exp - min_exp)
            if (max_exp - min_exp) > 1e-6
            else 0.0
        )
        cost = w_dur * norm_d + w_exp * norm_e
        er["normalized_duration_score"] = round(norm_d, 3)
        er["normalized_exposure_score"] = round(norm_e, 3)
        er["composite_cost"] = round(cost, 3)

    fastest_route = min(evaluated_routes, key=lambda x: x["duration_min"])
    max_allowed_duration = fastest_route["duration_min"] * max_detour_ratio

    eligible_eco = [
        er for er in evaluated_routes if er["duration_min"] <= max_allowed_duration
    ]
    if not eligible_eco:
        eligible_eco = evaluated_routes

    eco_route = min(eligible_eco, key=lambda x: (x["composite_cost"], x["exposure_proxy_index"]))

    fast_exp = fastest_route["exposure_proxy_index"]
    eco_exp = eco_route["exposure_proxy_index"]
    exposure_reduction_pct = (
        round(((fast_exp - eco_exp) / fast_exp) * 100.0, 1) if fast_exp > 0 else 0.0
    )
    additional_time_min = round(eco_route["duration_min"] - fastest_route["duration_min"], 1)
    distance_diff_km = round(eco_route["distance_km"] - fastest_route["distance_km"], 2)

    if fastest_route["route_id"] == eco_route["route_id"]:
        explanation = (
            f"The {fastest_route['route_name']} is both the fastest option "
            f"({fastest_route['duration_min']} min) and achieves the lowest estimated pollution "
            f"exposure proxy ({fastest_route['exposure_proxy_index']} AQI-hours) within the "
            f"configured {max_detour_ratio:.2f}x detour limit."
        )
    else:
        explanation = (
            f"Recommended Eco-Friendly Route: '{eco_route['route_name']}' reduces the estimated "
            f"AQI-time exposure proxy by {exposure_reduction_pct}% compared to the Fastest Route "
            f"('{fastest_route['route_name']}'), at the cost of +{additional_time_min} min "
            f"additional travel time ({distance_diff_km:+.2f} km) using weights "
            f"(Duration={w_dur:.2f}, Exposure={w_exp:.2f})."
        )

    methodology_note = (
        "Exposure Proxy = Mean Corridor Estimated AQI x Travel Duration (hours). "
        "Cost = w_duration x Norm(Duration) + w_exposure x Norm(Exposure). "
        "Note: AQI is a non-linear regulatory index; this proxy represents relative time-integrated "
        "corridor pollution exposure, not a clinical inhaled dose."
    )

    warnings.append(
        "Open-Meteo Air Quality provides regional grid estimates (~10 km resolution). "
        "Corridor differences incorporate synthetic diurnal traffic emission adjustments."
    )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "routing_source": routing_res["routing_source"],
        "is_fallback_routing": routing_res["is_fallback_routing"],
        "environmental_source": ", ".join(sorted(env_sources)),
        "fastest_route_id": fastest_route["route_id"],
        "eco_route_id": eco_route["route_id"],
        "exposure_reduction_pct": exposure_reduction_pct,
        "additional_time_min": additional_time_min,
        "distance_diff_km": distance_diff_km,
        "explanation": explanation,
        "methodology_note": methodology_note,
        "warnings": warnings,
        "routes": evaluated_routes,
    }
