import duckdb
import pandas as pd
import pytest

from b3_pulse.features.build import FEATURES_SQL

# Five consecutive trading days, closing prices chosen so the math is easy
# to check by hand: 10, 11, 12, 13, 14 (a flat +1 step each day).
SILVER_ROWS = """
values
    ('PETR4.SA', '2024-01-02', date '2024-01-02', 10.0, 1000),
    ('PETR4.SA', '2024-01-03', date '2024-01-03', 11.0, 1000),
    ('PETR4.SA', '2024-01-04', date '2024-01-04', 12.0, 1000),
    ('PETR4.SA', '2024-01-05', date '2024-01-05', 13.0, 1000),
    ('PETR4.SA', '2024-01-08', date '2024-01-08', 14.0, 1000)
"""
SILVER_COLUMNS = "(ticker, dt, trade_date, closing_price, trade_volume)"


def build_in_memory() -> pd.DataFrame:
    con = duckdb.connect()
    silver_source = f"({SILVER_ROWS}) as silver{SILVER_COLUMNS}"
    sql = FEATURES_SQL.format(silver_source=silver_source)
    return con.sql(sql).df().sort_values("trade_date").reset_index(drop=True)


def test_daily_return_is_pct_change_from_previous_close():
    df = build_in_memory()
    assert pd.isna(df.loc[0, "daily_return"])
    assert df.loc[1, "daily_return"] == pytest.approx(0.1)


def test_moving_average_only_looks_backward():
    df = build_in_memory()
    # 3rd row (12.0): average of the 3 rows seen so far (10, 11, 12)
    assert df.loc[2, "ma_5"] == pytest.approx(11.0)


def test_target_is_next_days_close_and_last_row_has_no_label():
    df = build_in_memory()
    assert df.loc[0, "target_next_close"] == 11.0
    assert df.loc[3, "target_next_close"] == 14.0
    assert pd.isna(df.loc[4, "target_next_close"])
