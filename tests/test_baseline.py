import numpy as np
import pandas as pd

from b3_pulse.models.baseline.train import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    chronological_split,
    naive_baseline_maes,
    split_params,
    train_and_evaluate,
)


def make_synthetic_dataset(n: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    closing_price = 10 + np.cumsum(rng.normal(0, 0.1, n))
    df = pd.DataFrame(
        {
            "trade_date": pd.date_range("2024-01-01", periods=n, freq="B"),
            "closing_price": closing_price,
            "trade_volume": rng.integers(1000, 5000, n),
            "daily_return": np.concatenate([[np.nan], np.diff(closing_price) / closing_price[:-1]]),
            "ma_5": pd.Series(closing_price).rolling(5, min_periods=1).mean(),
            "ma_10": pd.Series(closing_price).rolling(10, min_periods=1).mean(),
            "volatility_5": pd.Series(closing_price).rolling(5, min_periods=1).std(),
        }
    )
    df[TARGET_COLUMN] = df["closing_price"].shift(-1)
    return df.dropna(subset=[*FEATURE_COLUMNS, TARGET_COLUMN]).reset_index(drop=True)


def test_chronological_split_never_shuffles():
    df = make_synthetic_dataset()
    train_df, test_df = chronological_split(df, test_size=0.2)

    assert train_df["trade_date"].max() < test_df["trade_date"].min()
    assert len(train_df) + len(test_df) == len(df)


def test_train_and_evaluate_returns_expected_metric_keys():
    df = make_synthetic_dataset()
    train_df, test_df = chronological_split(df, test_size=0.2)

    _, metrics = train_and_evaluate(train_df, test_df)

    assert set(metrics) == {"mae", "rmse", "mape", "persistence_mae", "ma5_mae"}
    assert all(value >= 0 for value in metrics.values())


def test_train_and_evaluate_is_reproducible():
    df = make_synthetic_dataset()
    train_df, test_df = chronological_split(df, test_size=0.2)

    _, first = train_and_evaluate(train_df, test_df)
    _, second = train_and_evaluate(train_df, test_df)

    assert first == second


def test_naive_baseline_maes_match_hand_computed_values():
    test_df = pd.DataFrame(
        {
            "closing_price": [10.0, 11.0, 12.0],
            "ma_5": [9.0, 10.0, 11.0],
            TARGET_COLUMN: [11.0, 12.0, 12.0],
        }
    )

    maes = naive_baseline_maes(test_df)

    # persistence errors: 1, 1, 0 -> 2/3; ma_5 errors: 2, 2, 1 -> 5/3
    assert np.isclose(maes["persistence_mae"], 2 / 3)
    assert np.isclose(maes["ma5_mae"], 5 / 3)


def test_split_params_record_the_cutoff():
    df = make_synthetic_dataset()
    train_df, test_df = chronological_split(df, test_size=0.2)

    params = split_params(train_df, test_df)

    assert params["train_start"] == str(df["trade_date"].min().date())
    assert params["test_end"] == str(df["trade_date"].max().date())
    assert params["train_end"] < params["test_start"]
