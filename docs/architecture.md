# Architecture & rebuild plan

## Origin

Three separate postgrad (Pós Tech / FIAP MLET) capstone briefs, done as
sequential term projects, all against B3/Bovespa-style stock data:

- **Fase 2** — batch pipeline: scrape B3, land raw Parquet in S3, S3-event
  triggers a Lambda that starts a *visual-mode* Glue ETL job (required
  transforms: numeric aggregation, renaming two columns, a date calculation),
  refined output partitioned by date+ticker, auto-cataloged in Glue Catalog,
  queryable in Athena.
- **Fase 3** — an API ingesting data into a DB/DW/Data Lake (explicitly
  allowed to reuse Fase 2's source), a trained ML model, GitHub + docs, a
  storytelling video, served via a simple app/dashboard.
- **Fase 4** — an LSTM forecasting a chosen stock's closing price, full
  pipeline from `yfinance` data through training/evaluation (MAE/RMSE/MAPE)
  to a Dockerized FastAPI/Flask `/predict` endpoint with basic production
  monitoring.

Originals are archived in `docs/original-tech-challenges/`.

## Why rebuild as one project instead of three

The three briefs are stages of one maturity ladder — batch ingestion →
served ML → deep learning with MLOps — on the same domain, and Fase 3
explicitly permits reusing Fase 2's data source. Treating them as one
pipeline (rather than three unrelated repos) makes both the engineering and
the resulting case-study narrative stronger.

## Decisions made

- **Scope**: single ticker to start (`PETR4.SA` by default, swappable via
  `.env`), not a basket — a fully working single-ticker pipeline is a
  stronger, more finishable story than five shallow ones. Scaling to a
  small Ibovespa basket is a plausible future chapter once the core works.
- **Infra**: local-first. MinIO stands in for S3, DuckDB stands in for
  Glue/Athena — same architectural shape (bronze/silver lakehouse, SQL
  transforms, a queryable catalog) as the original AWS design, zero cloud
  cost, fully runnable offline.
- **Transforms as code**: DuckDB SQL replaces Glue's visual/no-code job —
  same three required transformation types (aggregate, rename, date-calc),
  but reviewable in a diff and unit-testable.
- **Build in parts, not one massive commit**: each part below should land
  as its own reviewable slice.

## Parts

### Part 1 — Ingestion + lakehouse (done)

`src/b3_pulse/ingestion/`, `src/b3_pulse/transform/`, `src/b3_pulse/lake.py`.

- `ingestion/fetch.py`: pulls daily OHLCV via `yfinance`, writes one Parquet
  file per trading day to `s3://bronze/<ticker>/dt=<date>/data.parquet`.
- `transform/refine.py`: DuckDB SQL bronze → silver. Implements the three
  required transform types from Fase 2's brief:
  - **A** (aggregation): `sum(volume)`, `max(high)`, `min(low)` grouped by
    ticker + trading day.
  - **B** (rename): `close` → `closing_price`, `volume` → `trade_volume`.
  - **C** (date calc): `days_since_last_session`, a lag-based gap in
    trading days (surfaces weekends/holidays; useful as a model feature
    later).
  - Output: `s3://silver/`, partitioned by `(ticker, dt)`.
- `transform/catalog.py`: registers the silver Parquet as a view
  (`warehouse.refined_quotes`) in a persisted DuckDB file
  (`data/processed/warehouse.duckdb`) — the local analog of
  Glue Catalog + Athena. **Must be opened via `open_warehouse()`**, not a
  bare `duckdb.connect(path)` — DuckDB's S3 credentials are session-scoped
  and aren't stored in the `.duckdb` file itself.
- `infra/docker-compose.yml`: MinIO + an `mc` init container that creates
  the `bronze`/`silver` buckets on first boot.

Not built in Part 1 (deliberately out of scope): the optional streaming
Bitcoin pipeline from the original Fase 2 brief. Worth a "bonus" section in
the writeup, not core path.

### Part 2 — Feature store + served baseline model (next)

- FastAPI ingestion endpoint writing into the same lake.
- A baseline model (e.g. gradient boosting) trained on `refined_quotes` +
  engineered features — gives an honest baseline to compare the LSTM
  against later.
- MLflow for experiment tracking / model registry.
- Streamlit dashboard as the "productive" surface Fase 3's brief requires.

### Part 3 — Deep learning + MLOps (blocked on ML server, resumes next week)

- LSTM trained on the same silver data.
- Model versioned in the MLflow registry.
- FastAPI `/predict`, Dockerized, deployed to a low-cost target.
- Structured logging + a `/metrics` endpoint; Grafana for latency/
  throughput; a rolling-MAE panel as a simple drift signal.
- CI/CD via GitHub Actions.

## Content plan

A 3-part Medium series mirroring the parts above, plus a "revisiting my
postgrad capstones as an ML engineer" LinkedIn hook post tying it together.
