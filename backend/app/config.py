import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models_store"

DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)


class Settings:
    PROJECT_NAME: str = "Traffic-Induced Pollution & Eco-Route System"
    VERSION: str = "1.0.0"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'app_data.db'}"
    )
    SYNTHETIC_CSV_PATH: Path = Path(
        os.getenv("SYNTHETIC_CSV_PATH", str(DATA_DIR / "synthetic_bengaluru_data.csv"))
    )
    ACTIVE_CSV_PATH: Path = Path(
        os.getenv("ACTIVE_CSV_PATH", str(DATA_DIR / "synthetic_bengaluru_data.csv"))
    )
    MODEL_ARTIFACT_PATH: Path = Path(
        os.getenv("MODEL_ARTIFACT_PATH", str(MODELS_DIR / "rf_aqi_model.joblib"))
    )

    OPEN_METEO_WEATHER_URL: str = os.getenv(
        "OPEN_METEO_WEATHER_URL", "https://api.open-meteo.com/v1/forecast"
    )
    OPEN_METEO_AQ_URL: str = os.getenv(
        "OPEN_METEO_AQ_URL", "https://air-quality-api.open-meteo.com/v1/air-quality"
    )
    OSRM_BASE_URL: str = os.getenv(
        "OSRM_BASE_URL", "https://router.project-osrm.org"
    )

    HTTP_TIMEOUT_SECONDS: float = float(os.getenv("HTTP_TIMEOUT_SECONDS", "8.0"))
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))

    DEFAULT_CITY: str = "Bengaluru"
    DEFAULT_LAT: float = 12.9716
    DEFAULT_LON: float = 77.5946

    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]


settings = Settings()
