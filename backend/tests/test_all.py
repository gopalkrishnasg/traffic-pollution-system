import io
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.ml.preprocessing import map_aqi_category

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["model_version"] is not None


def test_aqi_category_mapping():
    us_good = map_aqi_category(35.0, standard="US_AQI")
    assert us_good["category"] == "Good"

    us_unhealthy = map_aqi_category(165.0, standard="US_AQI")
    assert us_unhealthy["category"] == "Unhealthy"

    eu_fair = map_aqi_category(30.0, standard="EU_AQI")
    assert eu_fair["category"] == "Fair (EU)"


def test_model_metrics_and_feature_importance():
    metrics_resp = client.get("/api/model/metrics")
    assert metrics_resp.status_code == 200
    m = metrics_resp.json()
    assert m["is_trained"] is True
    assert "mae" in m and m["mae"] >= 0.0
    assert "rmse" in m and m["rmse"] >= 0.0
    assert "r2" in m

    fi_resp = client.get("/api/model/feature-importance")
    assert fi_resp.status_code == 200
    fi = fi_resp.json()
    assert len(fi["importances"]) > 0


@patch("app.api.routes.fetch_weather_data")
@patch("app.api.routes.fetch_air_quality_data")
def test_prediction_and_history_storage(mock_aq, mock_weather):
    mock_weather.return_value = {
        "latitude": 12.9177,
        "longitude": 77.6238,
        "timestamp": "2026-10-25T10:00:00Z",
        "temperature": 28.0,
        "relative_humidity": 58.0,
        "wind_speed": 12.0,
        "precipitation": 0.0,
        "source": "MOCKED_OPEN_METEO_WEATHER",
        "is_cached": False,
        "is_fallback": False,
        "warning": None,
    }
    mock_aq.return_value = {
        "latitude": 12.9177,
        "longitude": 77.6238,
        "timestamp": "2026-10-25T10:00:00Z",
        "pm2_5": 45.0,
        "pm10": 90.0,
        "no2": 38.0,
        "o3": 42.0,
        "co": 600.0,
        "us_aqi": 124.0,
        "european_aqi": 55.0,
        "aqi_standard_reported": "US_AQI",
        "source": "MOCKED_OPEN_METEO_AQ",
        "is_cached": False,
        "is_fallback": False,
        "warning": None,
    }

    payload = {
        "location_label": "Silk Board Test Point",
        "latitude": 12.9177,
        "longitude": 77.6238,
        "prediction_mode": "HYBRID_LIVE_WEATHER_USER_TRAFFIC",
        "aqi_standard": "US_AQI",
        "traffic_volume": 4100.0,
        "traffic_speed": 18.0,
    }
    pred_resp = client.post("/api/predict", json=payload)
    assert pred_resp.status_code == 200
    pred_data = pred_resp.json()
    assert pred_data["predicted_aqi"] > 0
    pred_id = pred_data["prediction_id"]

    hist_resp = client.get(f"/api/history/{pred_id}")
    assert hist_resp.status_code == 200
    hist_item = hist_resp.json()
    assert hist_item["location_label"] == "Silk Board Test Point"


def test_missing_feature_imputation_in_manual_mode():
    # Supply only coordinates and traffic_volume; omit weather and pollutants to verify median imputation
    payload = {
        "location_label": "Partial Input Test",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "prediction_mode": "MANUAL_INPUT",
        "aqi_standard": "US_AQI",
        "traffic_volume": 3200.0,
    }
    resp = client.post("/api/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["imputed_features"]) > 0
    assert data["predicted_aqi"] > 0


def test_invalid_coordinates_rejected():
    bad_payload = {
        "location_label": "Invalid Lat",
        "latitude": 145.0,
        "longitude": 77.5946,
        "prediction_mode": "MANUAL_INPUT",
        "aqi_standard": "US_AQI",
    }
    resp = client.post("/api/predict", json=bad_payload)
    assert resp.status_code == 422


def test_correlation_endpoint():
    resp = client.get("/api/correlations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_variable"] == "aqi"
    assert len(data["correlations"]) > 0
    assert len(data["pearson_matrix"]) == len(data["matrix_variables"])


@patch("app.services.route_scoring.fetch_candidate_routes")
@patch("app.services.route_scoring.fetch_weather_data")
@patch("app.services.route_scoring.fetch_air_quality_data")
def test_route_scoring_and_comparison(mock_aq, mock_weather, mock_routes):
    mock_routes.return_value = {
        "routing_source": "MOCKED_OSRM",
        "is_fallback_routing": False,
        "warnings": [],
        "routes": [
            {
                "route_id": "route_1",
                "route_name": "Fast Arterial",
                "distance_km": 10.0,
                "duration_min": 22.0,
                "geometry": [[12.9177, 77.6238], [12.95, 77.68], [12.985, 77.7369]],
            },
            {
                "route_id": "route_2",
                "route_name": "Eco Bypass",
                "distance_km": 11.2,
                "duration_min": 24.5,
                "geometry": [[12.9177, 77.6238], [12.96, 77.70], [12.985, 77.7369]],
            },
        ],
    }
    mock_weather.return_value = {
        "latitude": 12.95,
        "longitude": 77.68,
        "timestamp": "2026-10-25T10:00:00Z",
        "temperature": 27.0,
        "relative_humidity": 60.0,
        "wind_speed": 11.0,
        "precipitation": 0.0,
        "source": "MOCKED_WEATHER",
        "is_cached": False,
        "is_fallback": False,
        "warning": None,
    }
    mock_aq.return_value = {
        "latitude": 12.95,
        "longitude": 77.68,
        "timestamp": "2026-10-25T10:00:00Z",
        "pm2_5": 38.0,
        "pm10": 75.0,
        "no2": 30.0,
        "o3": 40.0,
        "co": 500.0,
        "us_aqi": 105.0,
        "european_aqi": 50.0,
        "aqi_standard_reported": "US_AQI",
        "source": "MOCKED_AQ",
        "is_cached": False,
        "is_fallback": False,
        "warning": None,
    }

    req_body = {
        "origin_lat": 12.9177,
        "origin_lon": 77.6238,
        "origin_label": "Silk Board",
        "destination_lat": 12.9850,
        "destination_lon": 77.7369,
        "destination_label": "Whitefield",
        "duration_weight": 0.3,
        "exposure_weight": 0.7,
        "max_detour_ratio": 1.4,
    }
    resp = client.post("/api/routes/compare", json=req_body)
    assert resp.status_code == 200
    res = resp.json()
    assert res["fastest_route_id"] == "route_1"
    assert len(res["routes"]) == 2
    assert "explanation" in res


def test_dataset_upload_validation():
    bad_csv = b"col1,col2\n1,2\n3,4\n"
    resp = client.post(
        "/api/datasets/upload",
        files={"file": ("invalid.csv", io.BytesIO(bad_csv), "text/csv")},
    )
    assert resp.status_code == 400
    assert "aqi" in resp.json()["detail"].lower()