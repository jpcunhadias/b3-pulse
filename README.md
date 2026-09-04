# b3-pulse

A local-first B3 (Bovespa) market-data platform: batch ingestion into a
medallion lakehouse, a feature store, a baseline ML model, and (in
progress) an LSTM forecaster — each served through a FastAPI service and a
Streamlit dashboard. Runs entirely offline against MinIO (S3-compatible)
and DuckDB, no cloud account required.

Design rationale and the part-by-part build log live in
[`docs/architecture.md`](docs/architecture.md). Course-issued source
material this project was originally scoped from is kept locally, outside
version control — not published in this repo.

## Status

| Part | Scope | Status |
|---|---|---|
| 1 | Ingestion + lakehouse (bronze/silver) | Done |
| 2 | Feature store + baseline model + API + dashboard | Done |
| 3 | LSTM forecaster + MLOps | Not started |

## Architecture

```
yfinance ──▶ bronze (MinIO, raw parquet, daily partition)
              │  transform/refine.py  (DuckDB SQL: aggregate, rename, date-calc)
              ▼
            silver (MinIO, refined parquet, partitioned by ticker+date)
              │  features/build.py  (DuckDB window functions)
              ▼
            features (MinIO, gold layer: returns, moving averages, volatility, label)
              │
              ├─▶ models/baseline/train.py ──▶ MLflow (tracking + registry, sqlite)
              │
     warehouse.duckdb  (local catalog: refined_quotes / features views)
              │
              ▼
       api/app.py (FastAPI)  ──▶  dashboard/app.py (Streamlit)
```

## Project layout

```
src/b3_pulse/
  config.py     Settings (ticker, MinIO, MLflow) via pydantic-settings + .env
  lake.py       Shared DuckDB connection wired to MinIO; bucket path helpers
  ingestion/    fetch.py        -- yfinance -> bronze parquet
  transform/    refine.py       -- bronze -> silver (DuckDB SQL)
                catalog.py      -- registers views in the local warehouse
  features/     build.py        -- silver -> gold feature store
  models/
    baseline/   train.py        -- GradientBoostingRegressor, MLflow-tracked
    lstm/       (part 3, not yet built)
  api/          app.py, service.py, schemas.py -- FastAPI service
  dashboard/    app.py          -- Streamlit UI, consumes the API over HTTP
infra/          docker-compose.yml -- local MinIO + bucket bootstrap
tests/          SQL-logic and API unit tests (no live infra required)
```

## Setup

```bash
cp .env.example .env                        # defaults to ticker PETR4.SA
docker compose -f infra/docker-compose.yml up -d
```

MinIO console: http://localhost:9001 (`b3pulse` / `b3pulse123`).

## Running the pipeline

```bash
uv run b3-pulse                              # ingest -> refine -> build features -> register warehouse views
uv run python -m b3_pulse.models.baseline.train
```

## Running the service

```bash
uv run b3-pulse-api                                     # http://localhost:8000
uv run streamlit run src/b3_pulse/dashboard/app.py      # http://localhost:8501
```

### API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/ingest` | Runs ingest → refine → build-features for a ticker |
| GET | `/quotes` | Recent refined quotes (for charting) |
| GET | `/predict` | Next-day close prediction from the current champion model |
| GET | `/model/metrics` | Latest training run's MAE / RMSE / MAPE |

## Inspecting data and model runs

```bash
uv run python -c "
from b3_pulse.transform.catalog import open_warehouse
print(open_warehouse().sql('select * from warehouse.features order by trade_date').df())
"

uv run mlflow ui --backend-store-uri sqlite:///mlflow.db
```

## Development

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```
