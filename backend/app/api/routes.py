import io
import json
import re
from datetime import datetime, timezone
from typing import List
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import PredictionRecord, RouteComparisonRecord
from app.schemas import (
    WeatherResponse,
    AirQualityResponse,
    TrafficResponse,
    PredictRequest,
    PredictResponse,
    ModelMetricsResponse,
    FeatureImportanceResponse,
    FeatureImportanceItem,
    CorrelationResponse,
    RouteCompareRequest,
    RouteCompareResponse,
    HistoryRecordOut,
)
from app.services.weather_service import fetch_weather_data
from app.services.air_quality_service import fetch_air_quality_data
from app.services.traffic_service import estimate_corridor_traffic
from app.services.route_scoring import evaluate_and_compare_routes
from app.ml.dataset_loader import load_active_dataset, generate_synthetic_bengaluru_dataset
from app.ml.trainer import train_random_forest_model
from app.ml.predictor import model_manager
from app.ml.correlation import compute_correlations
from app.ml.preprocessing import clean_and_align_dataset

router = APIRouter(prefix="/api")


@router.get("/health")
def health_check():
    artifact = model_manager.ensure_loaded()
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_loaded": artifact is not None,
        "model_version": artifact.get("model_version") if artifact else None,
    }


@router.get("/data/status")
def get_data_status():
    df, meta = load_active_dataset()
    return {
        "active_dataset": meta["dataset_name"],
        "is_synthetic": meta["is_synthetic"],
        "row_count": meta["row_count"],
        "available_features": meta["available_features"],
        "has_target_aqi": meta["has_target_aqi"],
        "cleaning_notes": meta["cleaning_notes"],
        "default_city": settings.DEFAULT_CITY,
        "default_coordinates": {
            "latitude": settings.DEFAULT_LAT,
            "longitude": settings.DEFAULT_LON,
        },
    }


@router.get("/weather", response_model=WeatherResponse)
def get_weather(
    latitude: float = Query(default=settings.DEFAULT_LAT, ge=-90.0, le=90.0),
    longitude: float = Query(default=settings.DEFAULT_LON, ge=-180.0, le=180.0),
):
    return fetch_weather_data(latitude, longitude)


@router.get("/air-quality", response_model=AirQualityResponse)
def get_air_quality(
    latitude: float = Query(default=settings.DEFAULT_LAT, ge=-90.0, le=90.0),
    longitude: float = Query(default=settings.DEFAULT_LON, ge=-180.0, le=180.0),
):
    return fetch_air_quality_data(latitude, longitude)


@router.get("/traffic", response_model=TrafficResponse)
def get_traffic_estimate(
    latitude: float = Query(default=settings.DEFAULT_LAT, ge=-90.0, le=90.0),
    longitude: float = Query(default=settings.DEFAULT_LON, ge=-180.0, le=180.0),
):
    return estimate_corridor_traffic(latitude, longitude)


@router.get("/dashboard/summary")
def get_dashboard_summary(
    latitude: float = Query(default=settings.DEFAULT_LAT, ge=-90.0, le=90.0),
    longitude: float = Query(default=settings.DEFAULT_LON, ge=-180.0, le=180.0),
    db: Session = Depends(get_db),
):
    weather = fetch_weather_data(latitude, longitude)
    aq = fetch_air_quality_data(latitude, longitude)
    traffic = estimate_corridor_traffic(latitude, longitude)
    df, meta = load_active_dataset()
    artifact = model_manager.ensure_loaded()

    # Compute current model prediction using available weather/AQ + diurnal traffic
    pred_aqi, cat_info, used_feats, _, _ = model_manager.predict_aqi(
        {
            "traffic_volume": traffic["traffic_volume"],
            "traffic_speed": traffic["traffic_speed"],
            "temperature": weather.get("temperature"),
            "relative_humidity": weather.get("relative_humidity"),
            "wind_speed": weather.get("wind_speed"),
            "precipitation": weather.get("precipitation"),
            "pm2_5": aq.get("pm2_5"),
            "pm10": aq.get("pm10"),
            "no2": aq.get("no2"),
            "o3": aq.get("o3"),
            "co": aq.get("co"),
        }
    )

    # Extract trend slice (last 36 records from dataset)
    trend_df = df.tail(36)
    trend_records = []
    for _, row in trend_df.iterrows():
        trend_records.append(
            {
                "timestamp": str(row.get("timestamp", ""))[-8:-3] or str(row.get("timestamp", "")),
                "location": str(row.get("location_name", "Bengaluru")),
                "aqi": float(row["aqi"]) if pd.notna(row.get("aqi")) else None,
                "pm2_5": float(row["pm2_5"]) if pd.notna(row.get("pm2_5")) else None,
                "traffic_volume": (
                    float(row["traffic_volume"]) if pd.notna(row.get("traffic_volume")) else None
                ),
            }
        )

    recent_preds = (
        db.query(PredictionRecord).order_by(PredictionRecord.created_at.desc()).limit(5).all()
    )
    recent_list = [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat(),
            "location_label": r.location_label,
            "predicted_aqi": r.predicted_aqi,
            "aqi_category": r.aqi_category,
            "data_source": r.data_source,
            "is_synthetic": bool(r.is_synthetic),
        }
        for r in recent_preds
    ]

    return {
        "city": settings.DEFAULT_CITY,
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "observed_air_quality": aq,
        "predicted_snapshot": {
            "predicted_aqi": pred_aqi,
            "category": cat_info["category"],
            "color": cat_info["color"],
            "note": cat_info["note"],
            "model_version": artifact["model_version"],
            "used_features": used_feats,
        },
        "weather": weather,
        "traffic": traffic,
        "model_metrics": {
            "model_version": artifact["model_version"],
            "is_synthetic_dataset": artifact["is_synthetic_dataset"],
            "mae": artifact["metrics"]["mae"],
            "rmse": artifact["metrics"]["rmse"],
            "r2": artifact["metrics"]["r2"],
            "train_samples": artifact["train_samples"],
            "test_samples": artifact["test_samples"],
        },
        "dataset_status": meta,
        "historical_trend": trend_records,
        "recent_predictions": recent_list,
    }


@router.post("/predict", response_model=PredictResponse)
def predict_aqi_endpoint(req: PredictRequest, db: Session = Depends(get_db)):
    warnings: List[str] = []
    raw_inputs = {
        "traffic_volume": req.traffic_volume,
        "traffic_speed": req.traffic_speed,
        "temperature": req.temperature,
        "relative_humidity": req.relative_humidity,
        "wind_speed": req.wind_speed,
        "precipitation": req.precipitation,
        "pm2_5": req.pm2_5,
        "pm10": req.pm10,
        "no2": req.no2,
        "o3": req.o3,
        "co": req.co,
    }

    is_synthetic = False
    sources_used = []

    if req.prediction_mode == "HYBRID_LIVE_WEATHER_USER_TRAFFIC":
        weather = fetch_weather_data(req.latitude, req.longitude)
        aq = fetch_air_quality_data(req.latitude, req.longitude)
        sources_used.extend([weather["source"], aq["source"]])
        if weather.get("is_fallback") or aq.get("is_fallback"):
            is_synthetic = True
            warnings.append("Live weather/AQ API fallback triggered; using demonstration values.")

        for k in ["temperature", "relative_humidity", "wind_speed", "precipitation"]:
            if raw_inputs[k] is None:
                raw_inputs[k] = weather.get(k)
        for k in ["pm2_5", "pm10", "no2", "o3", "co"]:
            if raw_inputs[k] is None:
                raw_inputs[k] = aq.get(k)

        if raw_inputs["traffic_volume"] is None or raw_inputs["traffic_speed"] is None:
            tr = estimate_corridor_traffic(req.latitude, req.longitude)
            raw_inputs["traffic_volume"] = raw_inputs["traffic_volume"] or tr["traffic_volume"]
            raw_inputs["traffic_speed"] = raw_inputs["traffic_speed"] or tr["traffic_speed"]
            sources_used.append(tr["source"])
            is_synthetic = True
            warnings.append(
                "Traffic volume/speed was not manually provided; filled using synthetic diurnal Bengaluru traffic simulator."
            )
        else:
            sources_used.append("USER_SUPPLIED_TRAFFIC")

    elif req.prediction_mode == "SYNTHETIC_DEMO":
        tr = estimate_corridor_traffic(req.latitude, req.longitude)
        raw_inputs["traffic_volume"] = raw_inputs["traffic_volume"] or tr["traffic_volume"]
        raw_inputs["traffic_speed"] = raw_inputs["traffic_speed"] or tr["traffic_speed"]
        sources_used.append("SYNTHETIC_DEMO_PRESET")
        is_synthetic = True
        warnings.append("Prediction executed in Synthetic Demonstration Mode.")
    else:
        sources_used.append("MANUAL_USER_INPUT")

    pred_val, cat_info, used_features, imputed_features, artifact = model_manager.predict_aqi(
        raw_inputs, aqi_standard=req.aqi_standard
    )

    if artifact.get("is_synthetic_dataset"):
        is_synthetic = True
        warnings.append(
            "Underlying Random Forest model was trained on the synthetic Bengaluru demonstration dataset."
        )

    if imputed_features:
        warnings.append(
            f"Missing features imputed with training medians: {', '.join(imputed_features)}."
        )

    data_source_str = " + ".join(sorted(set(sources_used)))
    record = PredictionRecord(
        location_label=req.location_label,
        latitude=req.latitude,
        longitude=req.longitude,
        prediction_mode=req.prediction_mode,
        aqi_standard=req.aqi_standard,
        predicted_aqi=pred_val,
        aqi_category=cat_info["category"],
        input_features_json=json.dumps(used_features),
        model_version=artifact["model_version"],
        data_source=data_source_str,
        is_synthetic=1 if is_synthetic else 0,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "prediction_id": record.id,
        "timestamp": record.created_at.isoformat(),
        "location_label": record.location_label,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "prediction_mode": record.prediction_mode,
        "aqi_standard": record.aqi_standard,
        "predicted_aqi": pred_val,
        "aqi_category": cat_info["category"],
        "category_color": cat_info["color"],
        "cautionary_note": (
            f"{cat_info['note']} Disclaimer: This value is a statistical model estimate, "
            "not an official regulatory sensor reading or medical health advisory."
        ),
        "used_features": used_features,
        "imputed_features": imputed_features,
        "data_source": data_source_str,
        "is_synthetic": is_synthetic,
        "model_version": artifact["model_version"],
        "model_metrics": artifact["metrics"],
        "warnings": warnings,
    }


@router.get("/model/metrics", response_model=ModelMetricsResponse)
def get_model_metrics():
    artifact = model_manager.ensure_loaded()
    return {
        "is_trained": True,
        "model_version": artifact["model_version"],
        "trained_at": artifact["trained_at"],
        "dataset_source": artifact["dataset_source"],
        "is_synthetic_dataset": artifact["is_synthetic_dataset"],
        "target_column": artifact["target_column"],
        "target_definition": artifact["target_definition"],
        "feature_names": artifact["feature_names"],
        "train_samples": artifact["train_samples"],
        "test_samples": artifact["test_samples"],
        "split_method": artifact["split_method"],
        "mae": artifact["metrics"]["mae"],
        "rmse": artifact["metrics"]["rmse"],
        "r2": artifact["metrics"]["r2"],
        "notes": artifact["notes"],
    }


@router.get("/model/feature-importance", response_model=FeatureImportanceResponse)
def get_feature_importance():
    artifact = model_manager.ensure_loaded()
    imp_dict = artifact.get("feature_importances", {})
    sorted_items = sorted(imp_dict.items(), key=lambda x: x[1], reverse=True)
    return {
        "model_version": artifact["model_version"],
        "is_synthetic_dataset": artifact["is_synthetic_dataset"],
        "importances": [
            FeatureImportanceItem(feature=k, importance=v) for k, v in sorted_items
        ],
    }


@router.post("/model/train", response_model=ModelMetricsResponse)
def trigger_model_training(exclude_pollutants: bool = Query(default=False)):
    try:
        artifact = train_random_forest_model(exclude_pollutants=exclude_pollutants)
        model_manager.reload_after_training(artifact)
        return {
            "is_trained": True,
            "model_version": artifact["model_version"],
            "trained_at": artifact["trained_at"],
            "dataset_source": artifact["dataset_source"],
            "is_synthetic_dataset": artifact["is_synthetic_dataset"],
            "target_column": artifact["target_column"],
            "target_definition": artifact["target_definition"],
            "feature_names": artifact["feature_names"],
            "train_samples": artifact["train_samples"],
            "test_samples": artifact["test_samples"],
            "split_method": artifact["split_method"],
            "mae": artifact["metrics"]["mae"],
            "rmse": artifact["metrics"]["rmse"],
            "r2": artifact["metrics"]["r2"],
            "notes": artifact["notes"],
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/correlations", response_model=CorrelationResponse)
def get_correlations():
    df, meta = load_active_dataset()
    try:
        return compute_correlations(
            df=df, is_synthetic=meta["is_synthetic"], dataset_name=meta["dataset_name"]
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/datasets")
def list_datasets():
    _, meta = load_active_dataset()
    csv_files = [p.name for p in settings.DATA_DIR.glob("*.csv")]
    return {
        "active_dataset": meta["dataset_name"],
        "is_synthetic": meta["is_synthetic"],
        "row_count": meta["row_count"],
        "available_features": meta["available_features"],
        "available_csv_files": sorted(csv_files),
    }


@router.post("/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are permitted.")

    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", file.filename)
    if ".." in safe_name or safe_name.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename.")

    raw_bytes = await file.read()
    if len(raw_bytes) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_BYTES} bytes.",
        )

    try:
        df = pd.read_csv(io.BytesIO(raw_bytes))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid CSV file format: {exc}") from exc

    cleaned_df, notes = clean_and_align_dataset(df)
    if "aqi" not in cleaned_df.columns:
        raise HTTPException(
            status_code=400,
            detail="Uploaded CSV must contain an 'aqi' (or 'us_aqi') target column.",
        )
    if len(cleaned_df) < 30:
        raise HTTPException(
            status_code=400,
            detail="Uploaded CSV must contain at least 30 valid rows after cleaning.",
        )

    dest_path = settings.DATA_DIR / safe_name
    cleaned_df.to_csv(dest_path, index=False)
    settings.ACTIVE_CSV_PATH = dest_path

    # Automatically retrain model on the newly uploaded dataset
    artifact = train_random_forest_model(
        df=cleaned_df, is_synthetic=False, dataset_name=safe_name
    )
    model_manager.reload_after_training(artifact)

    return {
        "message": f"Dataset '{safe_name}' validated, activated, and model retrained.",
        "dataset_name": safe_name,
        "rows_accepted": len(cleaned_df),
        "cleaning_notes": notes,
        "new_model_version": artifact["model_version"],
        "metrics": artifact["metrics"],
    }


@router.post("/datasets/reset-synthetic")
def reset_to_synthetic_dataset():
    syn_path = generate_synthetic_bengaluru_dataset(settings.SYNTHETIC_CSV_PATH)
    settings.ACTIVE_CSV_PATH = syn_path
    df, meta = load_active_dataset()
    artifact = train_random_forest_model(
        df=df, is_synthetic=True, dataset_name=meta["dataset_name"]
    )
    model_manager.reload_after_training(artifact)
    return {
        "message": "Reset active dataset to synthetic Bengaluru demonstration data and retrained model.",
        "dataset_name": meta["dataset_name"],
        "model_version": artifact["model_version"],
        "metrics": artifact["metrics"],
    }


@router.post("/routes/compare", response_model=RouteCompareResponse)
def compare_routes_endpoint(req: RouteCompareRequest, db: Session = Depends(get_db)):
    result = evaluate_and_compare_routes(
        origin_lat=req.origin_lat,
        origin_lon=req.origin_lon,
        destination_lat=req.destination_lat,
        destination_lon=req.destination_lon,
        duration_weight=req.duration_weight,
        exposure_weight=req.exposure_weight,
        max_detour_ratio=req.max_detour_ratio,
    )

    fastest_r = next(
        (r for r in result["routes"] if r["route_id"] == result["fastest_route_id"]),
        result["routes"][0],
    )
    eco_r = next(
        (r for r in result["routes"] if r["route_id"] == result["eco_route_id"]),
        result["routes"][0],
    )

    db_record = RouteComparisonRecord(
        origin_label=req.origin_label,
        origin_lat=req.origin_lat,
        origin_lon=req.origin_lon,
        destination_label=req.destination_label,
        destination_lat=req.destination_lat,
        destination_lon=req.destination_lon,
        fastest_route_id=result["fastest_route_id"],
        eco_route_id=result["eco_route_id"],
        fastest_duration_min=fastest_r["duration_min"],
        eco_duration_min=eco_r["duration_min"],
        exposure_reduction_pct=result["exposure_reduction_pct"],
        routing_source=result["routing_source"],
        environmental_source=result["environmental_source"],
        summary_json=json.dumps(
            {
                "explanation": result["explanation"],
                "fastest_aqi": fastest_r["average_aqi"],
                "eco_aqi": eco_r["average_aqi"],
            }
        ),
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    result["comparison_id"] = db_record.id
    return result


@router.get("/history", response_model=List[HistoryRecordOut])
def list_prediction_history(
    limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)
):
    rows = (
        db.query(PredictionRecord)
        .order_by(PredictionRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "created_at": r.created_at,
            "location_label": r.location_label,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "prediction_mode": r.prediction_mode,
            "aqi_standard": r.aqi_standard,
            "predicted_aqi": r.predicted_aqi,
            "aqi_category": r.aqi_category,
            "input_features": json.loads(r.input_features_json),
            "model_version": r.model_version,
            "data_source": r.data_source,
            "is_synthetic": bool(r.is_synthetic),
        }
        for r in rows
    ]


@router.get("/history/{prediction_id}", response_model=HistoryRecordOut)
def get_prediction_history_item(prediction_id: int, db: Session = Depends(get_db)):
    r = db.query(PredictionRecord).filter(PredictionRecord.id == prediction_id).first()
    if not r:
        raise HTTPException(status_code=404, detail=f"Prediction ID {prediction_id} not found.")
    return {
        "id": r.id,
        "created_at": r.created_at,
        "location_label": r.location_label,
        "latitude": r.latitude,
        "longitude": r.longitude,
        "prediction_mode": r.prediction_mode,
        "aqi_standard": r.aqi_standard,
        "predicted_aqi": r.predicted_aqi,
        "aqi_category": r.aqi_category,
        "input_features": json.loads(r.input_features_json),
        "model_version": r.model_version,
        "data_source": r.data_source,
        "is_synthetic": bool(r.is_synthetic),
    }