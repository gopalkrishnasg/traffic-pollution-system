from typing import Dict, Any, Tuple, List
import joblib
import pandas as pd
from app.config import settings
from app.ml.trainer import train_random_forest_model
from app.ml.preprocessing import map_aqi_category


class ModelManager:
    def __init__(self):
        self._artifact: Dict[str, Any] | None = None

    def ensure_loaded(self) -> Dict[str, Any]:
        if self._artifact is not None:
            return self._artifact

        artifact_path = settings.MODEL_ARTIFACT_PATH
        if not artifact_path.exists():
            self._artifact = train_random_forest_model()
        else:
            self._artifact = joblib.load(artifact_path)
        return self._artifact

    def reload_after_training(self, new_artifact: Dict[str, Any]) -> None:
        self._artifact = new_artifact

    def predict_aqi(
        self, raw_inputs: Dict[str, float | None], aqi_standard: str = "US_AQI"
    ) -> Tuple[float, Dict[str, str], Dict[str, float], List[str], Dict[str, Any]]:
        artifact = self.ensure_loaded()
        feature_names: List[str] = artifact["feature_names"]
        medians: Dict[str, float] = artifact["feature_medians"]
        pipeline = artifact["pipeline"]

        used_features: Dict[str, float] = {}
        imputed_features: List[str] = []

        row_data = {}
        for feat in feature_names:
            val = raw_inputs.get(feat)
            if val is None or pd.isna(val):
                fallback_val = float(medians.get(feat, 0.0))
                row_data[feat] = fallback_val
                used_features[feat] = round(fallback_val, 2)
                imputed_features.append(feat)
            else:
                clean_val = float(val)
                row_data[feat] = clean_val
                used_features[feat] = round(clean_val, 2)

        X_input = pd.DataFrame([row_data], columns=feature_names)
        raw_pred = float(pipeline.predict(X_input)[0])

        if aqi_standard == "EU_AQI":
            predicted_val = round(max(5.0, raw_pred * 0.55), 1)
        else:
            predicted_val = round(max(5.0, raw_pred), 1)

        category_info = map_aqi_category(predicted_val, standard=aqi_standard)
        return predicted_val, category_info, used_features, imputed_features, artifact


model_manager = ModelManager()
