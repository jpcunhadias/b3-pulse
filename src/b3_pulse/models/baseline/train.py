"""Baseline model: predicts next-day closing price from engineered features.

Gradient boosting over the gold-layer feature store. This is the honest
baseline the LSTM (Part 3) needs to beat to justify the extra complexity.
"""

import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    root_mean_squared_error,
)

from b3_pulse.config import settings
from b3_pulse.transform.catalog import open_warehouse

FEATURE_COLUMNS = ["closing_price", "trade_volume", "daily_return", "ma_5", "ma_10", "volatility_5"]
TARGET_COLUMN = "target_next_close"
MODEL_NAME = "b3-pulse-baseline"
MODEL_ALIAS = "champion"


def load_dataset(ticker: str) -> pd.DataFrame:
    con = open_warehouse()
    df = con.sql(f"""
        select * from warehouse.features
        where ticker = '{ticker}'
        order by trade_date
    """).df()
    con.close()
    return df.dropna(subset=[*FEATURE_COLUMNS, TARGET_COLUMN]).reset_index(drop=True)


def chronological_split(
    df: pd.DataFrame, test_size: float = 0.2
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Hold out the most recent rows as test — never shuffle time series data."""
    split_at = int(len(df) * (1 - test_size))
    return df.iloc[:split_at], df.iloc[split_at:]


def train_and_evaluate(
    train_df: pd.DataFrame, test_df: pd.DataFrame
) -> tuple[GradientBoostingRegressor, dict[str, float]]:
    x_train, y_train = train_df[FEATURE_COLUMNS], train_df[TARGET_COLUMN]
    x_test, y_test = test_df[FEATURE_COLUMNS], test_df[TARGET_COLUMN]

    model = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05)
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    metrics = {
        "mae": mean_absolute_error(y_test, predictions),
        "rmse": root_mean_squared_error(y_test, predictions),
        "mape": mean_absolute_percentage_error(y_test, predictions),
    }
    return model, metrics


def run(ticker: str | None = None, test_size: float = 0.2) -> dict[str, float]:
    ticker = ticker or settings.ticker
    df = load_dataset(ticker)
    train_df, test_df = chronological_split(df, test_size)
    model, metrics = train_and_evaluate(train_df, test_df)

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment)
    with mlflow.start_run():
        mlflow.log_param("ticker", ticker)
        mlflow.log_param("n_train", len(train_df))
        mlflow.log_param("n_test", len(test_df))
        mlflow.log_params(model.get_params())
        mlflow.log_metrics(metrics)
        model_info = mlflow.sklearn.log_model(model, name="model", registered_model_name=MODEL_NAME)

    version = model_info.registered_model_version
    mlflow.MlflowClient().set_registered_model_alias(MODEL_NAME, MODEL_ALIAS, version)

    return metrics


if __name__ == "__main__":
    result = run()
    print(f"Baseline metrics: {result}")
