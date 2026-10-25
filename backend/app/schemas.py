from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


class CoordinateMixin(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class WeatherResponse(CoordinateMixin):
    timestamp: str
    temperature: Optional[float] = None
    relative_humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    precipitation: Optional[float] = None
    source: str
    is_cached: bool = False
    is_fallback: bool = False
    warning: Optional[str] = None


class AirQualityResponse(CoordinateMixin):
    timestamp: str
    pm2_5: Optional[float] = None
    pm10: Optional[float] = None
    no2: Optional[float] = None
    o3: Optional[float] = None
    co: Optional[float] = None
    us_aqi: Optional[float] = None
    european_aqi: Optional[float] = None
    aqi_standard_reported: str = "US_AQI"
    source: str
    is_cached: bool = False
    is_fallback: bool = False
    warning: Optional[str] = None


class TrafficResponse(CoordinateMixin):
    timestamp: str
    traffic_volume: float
    traffic_speed: float
    congestion_level: str
    source: str
    is_synthetic: bool = True
    note: str


class PredictRequest(CoordinateMixin):
    location_label: str = Field(default="Bengaluru Selected Point", max_length=120)
    prediction_mode: str = Field(
        default="HYBRID_LIVE_WEATHER_USER_TRAFFIC",
        pattern="^(HYBRID_LIVE_WEATHER_USER_TRAFFIC|MANUAL_INPUT|SYNTHETIC_DEMO)$",
    )
    aqi_standard: str = Field(default="US_AQI", pattern="^(US_AQI|EU_AQI)$")
    traffic_volume: Optional[float] = Field(default=None, ge=0.0, le=25000.0)
    traffic_speed: Optional[float] = Field(default=None, ge=1.0, le=160.0)
    temperature: Optional[float] = Field(default=None, ge=-40.0, le=60.0)
    relative_humidity: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    wind_speed: Optional[float] = Field(default=None, ge=0.0, le=200.0)
    precipitation: Optional[float] = Field(default=None, ge=0.0, le=1000.0)
    pm2_5: Optional[float] = Field(default=None, ge=0.0, le=2000.0)
    pm10: Optional[float] = Field(default=None, ge=0.0, le=3000.0)
    no2: Optional[float] = Field(default=None, ge=0.0, le=1000.0)
    o3: Optional[float] = Field(default=None, ge=0.0, le=1000.0)
    co: Optional[float] = Field(default=None, ge=0.0, le=50000.0)


class PredictResponse(BaseModel):
    prediction_id: int
    timestamp: str
    location_label: str
    latitude: float
    longitude: float
    prediction_mode: str
    aqi_standard: str
    predicted_aqi: float
    aqi_category: str
    category_color: str
    cautionary_note: str
    used_features: Dict[str, float]
    imputed_features: List[str]
    data_source: str
    is_synthetic: bool
    model_version: str
    model_metrics: Dict[str, Any]
    warnings: List[str]


class ModelMetricsResponse(BaseModel):
    is_trained: bool
    model_version: str
    trained_at: Optional[str] = None
    dataset_source: str
    is_synthetic_dataset: bool
    target_column: str
    target_definition: str
    feature_names: List[str]
    train_samples: int
    test_samples: int
    split_method: str
    mae: float
    rmse: float
    r2: float
    notes: str


class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float


class FeatureImportanceResponse(BaseModel):
    model_version: str
    is_synthetic_dataset: bool
    importances: List[FeatureImportanceItem]


class CorrelationPair(BaseModel):
    variable: str
    pearson_r: Optional[float]
    spearman_rho: Optional[float]
    sample_count: int
    missing_count: int
    interpretation: str


class CorrelationResponse(BaseModel):
    dataset_name: str
    is_synthetic: bool
    total_rows: int
    target_variable: str
    correlations: List[CorrelationPair]
    matrix_variables: List[str]
    pearson_matrix: List[List[Optional[float]]]
    scatter_samples: List[Dict[str, Optional[float]]]
    warnings: List[str]


class RouteCompareRequest(BaseModel):
    origin_lat: float = Field(..., ge=-90.0, le=90.0)
    origin_lon: float = Field(..., ge=-180.0, le=180.0)
    origin_label: str = Field(default="Origin", max_length=120)
    destination_lat: float = Field(..., ge=-90.0, le=90.0)
    destination_lon: float = Field(..., ge=-180.0, le=180.0)
    destination_label: str = Field(default="Destination", max_length=120)
    duration_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    exposure_weight: float = Field(default=0.65, ge=0.0, le=1.0)
    max_detour_ratio: float = Field(default=1.45, ge=1.05, le=3.0)

    @field_validator("destination_lon")
    @classmethod
    def check_weights(cls, v, info):
        return v


class SamplePointInfo(BaseModel):
    latitude: float
    longitude: float
    estimated_aqi: float
    pm2_5: Optional[float] = None
    traffic_volume: float
    source: str


class EvaluatedRoute(BaseModel):
    route_id: str
    route_name: str
    distance_km: float
    duration_min: float
    average_aqi: float
    average_pm2_5: float
    exposure_proxy_index: float
    exposure_unit: str
    normalized_duration_score: float
    normalized_exposure_score: float
    composite_cost: float
    traffic_summary: str
    traffic_is_synthetic: bool
    environmental_source: str
    data_confidence: str
    geometry: List[List[float]]
    sample_points: List[SamplePointInfo]


class RouteCompareResponse(BaseModel):
    comparison_id: int
    timestamp: str
    routing_source: str
    is_fallback_routing: bool
    environmental_source: str
    fastest_route_id: str
    eco_route_id: str
    exposure_reduction_pct: float
    additional_time_min: float
    distance_diff_km: float
    explanation: str
    methodology_note: str
    warnings: List[str]
    routes: List[EvaluatedRoute]


class HistoryRecordOut(BaseModel):
    id: int
    created_at: datetime
    location_label: str
    latitude: float
    longitude: float
    prediction_mode: str
    aqi_standard: str
    predicted_aqi: float
    aqi_category: str
    input_features: Dict[str, Any]
    model_version: str
    data_source: str
    is_synthetic: bool
