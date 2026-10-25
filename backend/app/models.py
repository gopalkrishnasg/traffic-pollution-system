from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class PredictionRecord(Base):
    __tablename__ = "prediction_records"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    location_label = Column(String(120), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    prediction_mode = Column(String(50), nullable=False)
    aqi_standard = Column(String(30), nullable=False, default="US_AQI")
    predicted_aqi = Column(Float, nullable=False)
    aqi_category = Column(String(60), nullable=False)
    input_features_json = Column(Text, nullable=False)
    model_version = Column(String(60), nullable=False)
    data_source = Column(String(80), nullable=False)
    is_synthetic = Column(Integer, default=0, nullable=False)


class RouteComparisonRecord(Base):
    __tablename__ = "route_comparison_records"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    origin_label = Column(String(120), nullable=False)
    origin_lat = Column(Float, nullable=False)
    origin_lon = Column(Float, nullable=False)
    destination_label = Column(String(120), nullable=False)
    destination_lat = Column(Float, nullable=False)
    destination_lon = Column(Float, nullable=False)
    fastest_route_id = Column(String(50), nullable=False)
    eco_route_id = Column(String(50), nullable=False)
    fastest_duration_min = Column(Float, nullable=False)
    eco_duration_min = Column(Float, nullable=False)
    exposure_reduction_pct = Column(Float, nullable=False)
    routing_source = Column(String(80), nullable=False)
    environmental_source = Column(String(80), nullable=False)
    summary_json = Column(Text, nullable=False)