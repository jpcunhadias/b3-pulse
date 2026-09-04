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
2. **Feature store + served baseline model** — FastAPI ingestion endpoint,
   a baseline ML model, MLflow tracking, a Streamlit dashboard.
3. **Deep learning + MLOps** — LSTM forecaster on the same silver data,
   FastAPI `/predict`, Docker, basic monitoring. *(Resumes once the ML
   server is back online.)*

See `docs/architecture.md` for the full design and rationale.

## Layout

```
src/b3_pulse/
  ingestion/    fetch OHLCV -> bronze parquet
  transform/    bronze -> silver (DuckDB SQL) + local warehouse catalog
  features/     (part 2)
  models/
    baseline/   (part 2)
    lstm/       (part 3)
  api/          (parts 2-3)
  dashboard/    (part 2)
infra/          docker-compose for local MinIO
```

## Quickstart (Part 1)

```bash
cp .env.example .env        # defaults to PETR4.SA
docker compose -f infra/docker-compose.yml up -d
uv run b3-pulse              # ingest -> refine -> register warehouse view
```

Query the result:

```bash
uv run python -c "
from b3_pulse.transform.catalog import open_warehouse
print(open_warehouse().sql('select * from warehouse.refined_quotes order by trade_date').df())
"
```

MinIO console: http://localhost:9001 (`b3pulse` / `b3pulse123`).

## Dev

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```
