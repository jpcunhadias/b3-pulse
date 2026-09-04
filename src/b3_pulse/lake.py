"""Shared DuckDB connection wired to the local MinIO (S3-compatible) lakehouse."""

from urllib.parse import urlparse

import duckdb

from b3_pulse.config import settings


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")

    parsed = urlparse(settings.minio_endpoint)
    con.execute(f"""
        SET s3_endpoint = '{parsed.netloc}';
        SET s3_access_key_id = '{settings.minio_access_key}';
        SET s3_secret_access_key = '{settings.minio_secret_key}';
        SET s3_use_ssl = {"true" if parsed.scheme == "https" else "false"};
        SET s3_url_style = 'path';
    """)
    return con


def bronze_path(ticker: str) -> str:
    return f"s3://{settings.bronze_bucket}/{ticker}/*/*.parquet"


def silver_root() -> str:
    return f"s3://{settings.silver_bucket}"
