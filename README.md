# Traffic-Induced Pollution Correlation and Prediction Model with Eco-Friendly Route Recommendations

## 1. Project Title
**Traffic-Induced Pollution Correlation and Prediction Model with Eco-Friendly Route Recommendations (Default Demonstration City: Bengaluru, India)**

## 2. Abstract
Urban road congestion contributes significantly to localized spikes in particulate matter ($\text{PM}_{2.5}, \text{PM}_{10}$) and gaseous pollutants ($\text{NO}_2, \text{CO}$). Conventional navigation systems optimize exclusively for travel duration or distance without accounting for commuter pollution exposure. This project presents a full-stack decision-support and environmental analytics system that:
1. Quantifies statistical correlations (Pearson $r$ and Spearman $\rho$) between traffic volume, average speed, meteorological parameters, pollutant concentrations, and the Air Quality Index (AQI).
2. Trains a time-aware **Random Forest Regression** pipeline to predict corridor AQI without target leakage.
3. Integrates live weather and regional air-quality observations from **Open-Meteo APIs** alongside road geometry from **OSRM**.
4. Evaluates candidate routes between any user-selected origin and destination in Bengaluru to recommend both a **Fastest Route** and an **Eco-Friendly Route** that minimizes a time-integrated AQI exposure proxy subject to a configurable maximum detour constraint.

## 3. Problem Statement
Commuters, two-wheeler riders, and pedestrians traveling through high-congestion junctions in Indian metropolitan cities (such as Silk Board, Hebbal, and Majestic in Bengaluru) experience elevated pollution exposure. Existing tools either display static regional AQI values or provide traffic routing without coupling environmental modeling to route selection. Furthermore, many student prototypes conflate synthetic simulation data with live sensor measurements or suffer from temporal target leakage during machine learning evaluation.

## 4. Objectives
1. Build an automated data ingestion and validation pipeline supporting historical CSV uploads and a reproducible (`seed=42`) synthetic Bengaluru demonstration dataset.
2. Perform bivariate Pearson and Spearman correlation analyses with explicit sample-size checks and non-causal interpretations.
3. Train and persist a `RandomForestRegressor` model using chronological train/test splitting, reporting MAE, RMSE, and $R^2$.
4. Integrate live Open-Meteo Weather and Air Quality APIs with explicit US AQI vs. European AQI distinction and resilient offline fallback handling.
5. Implement a multi-objective route scoring engine on top of OpenStreetMap/OSRM road geometries to compare fastest and eco-friendly alternatives.

## 5. Existing-System Limitations
- Navigation apps optimize solely for travel time.
- Public AQI portals report coarse station averages without road-corridor exposure integration.
- Many academic ML implementations use random $k$-fold splits on autocorrelated time-series data, inflating $R^2$ scores via temporal leakage.

## 6. Proposed System
A modular FastAPI + React + SQLite architecture that strictly separates observed regional API data, synthetic diurnal traffic estimates, and Random Forest model predictions. Every UI card and database record carries an explicit provenance badge (`OPEN_METEO_LIVE`, `SYNTHETIC_SEED_42`, `OSRM_PUBLIC_API`, or `FALLBACK_DEMO`).

## 7. System Architecture
```text
[React 18 + Vite + Recharts + Leaflet SPA]
                 │  (REST JSON over HTTP)
                 ▼
[FastAPI Application Server (Uvicorn)]
  ├── /api/weather & /api/air-quality ──► Open-Meteo REST APIs (TTL Cached)
  ├── /api/routes/compare             ──► OSRM Routing API + RF Corridor Scorer
  ├── /api/predict & /api/model/*     ──► Scikit-Learn RandomForest (joblib)
  ├── /api/correlations & /api/datasets─► Pandas / SciPy Preprocessing Engine
  └── /api/history                    ──► SQLite Database via SQLAlchemy 2.0