from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.ml.dataset_loader import load_active_dataset
from app.ml.predictor import model_manager
from app.api.routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite tables, ensure synthetic fallback dataset exists, and warm-load model
    init_db()
    load_active_dataset()
    model_manager.ensure_loaded()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Academic engineering API for Traffic-Induced Pollution Correlation, "
        "Random Forest AQI Prediction, and Eco-Friendly Route Recommendations."
    ),
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)