"""Business logic behind the API routes -- kept separate from FastAPI wiring
so it stays testable/importable without spinning up an HTTP server.
"""

import mlflow
import pandas as pd

from b3_pulse.config import settings
from b3_pulse.features.build import build_features
from b3_pulse.ingestion.fetch import run as ingest_run
from b3_pulse.models.baseline.train import FEATURE_COLUMNS, MODEL_ALIAS, MODEL_NAME
from b3_pulse.transform.catalog import open_warehouse, register_features, register_refined_quotes
from b3_pulse.transform.refine import refine

MODEL_URI = f"models:/{MODEL_NAME}@{MODEL_ALIAS}"


def run_ingestion_pipeline(
    ticker: str | None, start_date: str | None, end_date: str | None
) -> dict:
    ticker = ticker or settings.ticker
    paths = ingest_run(ticker=ticker, start_date=start_date, end_date=end_date)
    refine(ticker)
    register_refined_quotes()
    build_features(ticker)
    register_features()

    con = open_warehouse()
    count_row = con.sql(
        f"select count(*) from warehouse.features where ticker = '{ticker}'"
    ).fetchone()
    con.close()
    feature_rows = count_row[0] if count_row else 0
    return {"ticker": ticker, "bronze_partitions": len(paths), "feature_rows": feature_rows}


def get_recent_quotes(ticker: str, limit: int = 90) -> pd.DataFrame:
    con = open_warehouse()
    df = con.sql(f"""
        select trade_date, closing_price, trade_volume
        from warehouse.refined_quotes
        where ticker = '{ticker}'
        order by trade_date desc
        limit {limit}
    """).df()
    con.close()
    return df.sort_values("trade_date").reset_index(drop=True)


def _latest_feature_row(ticker: str) -> pd.Series:
    con = open_warehouse()
    df = con.sql(f"""
        select * from warehouse.features
        where ticker = '{ticker}'
        order by trade_date desc
        limit 1
    """).df()
    con.close()
    if df.empty:
        raise ValueError(f"no features found for {ticker!r} -- run /ingest first")
    return df.iloc[0]


def predict_next_close(ticker: str) -> dict:
    row = _latest_feature_row(ticker)

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    model = mlflow.pyfunc.load_model(MODEL_URI)
    x = row[FEATURE_COLUMNS].to_frame().T
    prediction = float(model.predict(x)[0])

    return {
        "ticker": ticker,
        "as_of_date": str(row["trade_date"]),
        "last_close": float(row["closing_price"]),
        "predicted_next_close": prediction,
        "model_version": MODEL_URI,
    }


def get_latest_metrics(ticker: str) -> dict:
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    client = mlflow.MlflowClient()
    experiment = client.get_experiment_by_name(settings.mlflow_experiment)
    if experiment is None:
        raise ValueError("no MLflow experiment found -- train the baseline model first")

    runs = client.search_runs(
        [experiment.experiment_id],
        filter_string=f"params.ticker = '{ticker}'",
        order_by=["start_time DESC"],
        max_results=1,
    )
    if not runs:
        raise ValueError(f"no training runs found for {ticker!r}")

    run = runs[0]
    return {
        "run_id": run.info.run_id,
        "mae": run.data.metrics["mae"],
        "rmse": run.data.metrics["rmse"],
        "mape": run.data.metrics["mape"],
    }
