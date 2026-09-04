# b3-pulse

A local-first, modernized rebuild of a 3-part postgrad ML Engineering capstone
(batch data pipeline → served ML model → deep-learning forecaster), told as
one story on a single B3 ticker instead of three disconnected assignments.

Original briefs: `docs/original-tech-challenges/` (kept for reference —
see `docs/architecture.md` for how each maps onto this rebuild).

## Architecture

Medallion lakehouse, built up in parts:

1. **Ingestion + lakehouse** (this part) — pull daily OHLCV via `yfinance`,
   land raw Parquet in a **bronze** MinIO bucket (daily partition), refine
   into a **silver** bucket with DuckDB SQL (aggregation, renames, a
   date-gap calc), and register it as a queryable view in a local DuckDB
   "warehouse" file — the local stand-in for Glue Catalog + Athena.
2. **Feature store + served baseline model** (this part) — a gold-layer
   feature store, a `GradientBoostingRegressor` baseline tracked in MLflow,
   a FastAPI service, and a Streamlit dashboard consuming it.
3. **Deep learning + MLOps** — LSTM forecaster on the same silver data,
   FastAPI `/predict`, Docker, basic monitoring. *(Resumes once the ML
   server is back online.)*

See `docs/architecture.md` for the full design and rationale.

## Layout

```
src/b3_pulse/
  ingestion/    fetch OHLCV -> bronze parquet
  transform/    bronze -> silver (DuckDB SQL) + local warehouse catalog
  features/     silver -> gold feature store (DuckDB window functions)
  models/
    baseline/   gradient boosting on the feature store, tracked in MLflow
    lstm/       (part 3)
  api/          FastAPI service: /ingest, /quotes, /predict, /model/metrics
  dashboard/    Streamlit UI consuming the API
infra/          docker-compose for local MinIO
```

## Quickstart

```bash
cp .env.example .env        # defaults to PETR4.SA
docker compose -f infra/docker-compose.yml up -d
uv run b3-pulse              # ingest -> refine -> build features -> register warehouse views
uv run python -m b3_pulse.models.baseline.train
```

Serve the API and dashboard (separate terminals):

```bash
uv run b3-pulse-api                                    # http://localhost:8000
uv run streamlit run src/b3_pulse/dashboard/app.py     # http://localhost:8501
```

Query the lakehouse directly:

```bash
uv run python -c "
from b3_pulse.transform.catalog import open_warehouse
print(open_warehouse().sql('select * from warehouse.features order by trade_date').df())
"
```

Inspect model runs: `uv run mlflow ui --backend-store-uri sqlite:///mlflow.db`.

MinIO console: http://localhost:9001 (`b3pulse` / `b3pulse123`).

## Dev

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```
