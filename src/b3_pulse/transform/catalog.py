"""Local stand-in for Glue Catalog + Athena: a persisted DuckDB file with a
view over the silver Parquet dataset, queryable with plain SQL.
"""

from pathlib import Path

import duckdb

from b3_pulse.lake import connect, features_glob, silver_glob

WAREHOUSE_PATH = Path("data/processed/warehouse.duckdb")


def open_warehouse() -> duckdb.DuckDBPyConnection:
    """Return a connection with S3 credentials set and the view attached.

    DuckDB's S3 settings are session-scoped, not stored in the .duckdb file,
    so the warehouse must always be opened through here (not a bare
    `duckdb.connect(WAREHOUSE_PATH)`) for the view to resolve.
    """
    WAREHOUSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = connect()
    con.execute(f"ATTACH '{WAREHOUSE_PATH}' AS warehouse")
    return con


def register_view(con: duckdb.DuckDBPyConnection, name: str, glob: str) -> None:
    con.execute(f"""
        CREATE OR REPLACE VIEW warehouse.{name} AS
        SELECT * FROM read_parquet('{glob}', hive_partitioning = true)
    """)


def register_refined_quotes() -> Path:
    con = open_warehouse()
    register_view(con, "refined_quotes", silver_glob())
    con.close()
    return WAREHOUSE_PATH


def register_features() -> Path:
    con = open_warehouse()
    register_view(con, "features", features_glob())
    con.close()
    return WAREHOUSE_PATH


if __name__ == "__main__":
    path = register_refined_quotes()
    print(f"Registered warehouse.refined_quotes in {path}")
