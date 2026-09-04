import duckdb
import pandas as pd

from b3_pulse.transform.refine import REFINE_SQL

BRONZE_ROWS = """
values
    ('PETR4.SA', '2024-01-02', timestamp '2024-01-02', 10.0, 10.5, 9.8, 10.2, 1000),
    ('PETR4.SA', '2024-01-02', timestamp '2024-01-02', 10.2, 10.3, 10.0, 10.1, 500),
    ('PETR4.SA', '2024-01-03', timestamp '2024-01-03', 10.1, 10.9, 10.0, 10.8, 2000)
"""
BRONZE_COLUMNS = "(ticker, dt, date, open, high, low, close, volume)"


def refine_in_memory() -> duckdb.DuckDBPyRelation:
    con = duckdb.connect()
    bronze_source = f"({BRONZE_ROWS}) as bronze{BRONZE_COLUMNS}"
    sql = REFINE_SQL.format(bronze_source=bronze_source)
    return con.sql(sql)


def test_aggregates_multiple_rows_per_day():
    result = refine_in_memory().df()
    day_one = result[result["dt"] == "2024-01-02"].iloc[0]

    assert day_one["trade_volume"] == 1500  # A: summed across the two rows
    assert day_one["high"] == 10.5
    assert day_one["low"] == 9.8


def test_renames_close_and_volume():
    columns = set(refine_in_memory().columns)
    assert "closing_price" in columns
    assert "trade_volume" in columns
    assert "close" not in columns
    assert "volume" not in columns


def test_date_diff_since_previous_session():
    result = refine_in_memory().df().sort_values("trade_date")

    first_row, second_row = result.iloc[0], result.iloc[1]
    assert pd.isna(first_row["days_since_last_session"])
    assert second_row["days_since_last_session"] == 1
