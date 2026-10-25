from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline

from app.config import settings
from app.ml.dataset_loader import load_active_dataset
from app.ml.preprocessing import CANDIDATE_FEATURES


def train_random_forest_model(
    df: pd.DataFrame | None = None,
    is_synthetic: bool = True,
    dataset_name: str = "synthetic_bengaluru_data.csv",
    exclude_pollutants: bool = False,
) -> Dict[str, Any]:
    """
    Train a RandomForestRegressor to predict contemporaneous US AQI.
    Uses a chronological (time-ordered) 80/20 train/test split when timestamps exist
    to avoid temporal data leakage.
    """
    if df is None:
        df, meta = load_active_dataset()
        is_synthetic = meta["is_synthetic"]
        dataset_name = meta["dataset_name"]

    if "aqi" not in df.columns:
        raise ValueError(
            "Dataset does not contain target column 'aqi'. Ensure CSV includes 'aqi' or 'us_aqi'."
        )

    df_valid = df.dropna(subset=["aqi"]).copy()
    if len(df_valid) < 30:
        raise ValueError(
            f"Insufficient valid rows ({len(df_valid)}) for training. At least 30 rows required."
        )

    candidate_cols: List[str] = list(CANDIDATE_FEATURES)
    if exclude_pollutants:
        candidate_cols = [
            c for c in candidate_cols if c not in ("pm2_5", "pm10", "no2", "o3", "co")
        ]

    feature_names = [
        c for c in candidate_cols if c in df_valid.columns and df_valid[c].notna().sum() > 10
    ]
    if not feature_names:
        raise ValueError("No valid input feature columns found in dataset.")

    # Time-aware chronological split
    if "timestamp" in df_valid.columns and df_valid["timestamp"].notna().all():
        df_valid = df_valid.sort_values("timestamp").reset_index(drop=True)
        split_method = "CHRONOLOGICAL_TIME_ORDERED_80_20"
    else:
        split_method = "SEQUENTIAL_INDEX_80_20"

    split_idx = int(len(df_valid) * 0.8)
    train_df = df_valid.iloc[:split_idx]
    test_df = df_valid.iloc[split_idx:]

    X_train = train_df[feature_names]
    y_train = train_df["aqi"].values
    X_test = test_df[feature_names]
    y_test = test_df["aqi"].values

    pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "rf",
                RandomForestRegressor(
                    n_estimators=120,
                    max_depth=14,
                    min_samples_split=4,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)

    mae = float(mean_absolute_error(y_test, preds))
    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
    r2 = float(r2_score(y_test, preds))

    rf_step: RandomForestRegressor = pipeline.named_steps["rf"]
    imputer_step: SimpleImputer = pipeline.named_steps["imputer"]

    importances = {
        feat: round(float(imp), 4)
        for feat, imp in zip(feature_names, rf_step.feature_importances_)
    }
    medians = {
        feat: round(float(med), 3)
        for feat, med in zip(feature_names, imputer_step.statistics_)
    }

    trained_at = datetime.now(timezone.utc).isoformat()
    model_version = f"rf-v1-{'syn' if is_synthetic else 'real'}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"

    artifact = {
        "pipeline": pipeline,
        "model_version": model_version,
        "trained_at": trained_at,
        "dataset_source": dataset_name,
        "is_synthetic_dataset": is_synthetic,
        "target_column": "aqi",
        "target_definition": (
            "Contemporaneous US-EPA style AQI estimated from traffic, meteorological, "
            "and background pollutant features without target leakage."
        ),
        "feature_names": feature_names,
        "feature_medians": medians,
        "feature_importances": importances,
        "train_samples": len(train_df),
        "test_samples": len(test_df),
        "split_method": split_method,
        "metrics": {
            "mae": round(mae, 3),
            "rmse": round(rmse, 3),
            "r2": round(r2, 4),
        },
        "notes": (
            "SYNTHETIC DATA EVALUATION: Metrics reflect performance on the synthetic Bengaluru "
            "demonstration dataset (seed=42), not validated physical sensor accuracy."
            if is_synthetic
            else "HISTORICAL DATASET EVALUATION: Metrics computed on held-out chronological test split."
        ),
    }

    artifact_path: Path = settings.MODEL_ARTIFACT_PATH
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, artifact_path)
    return artifact