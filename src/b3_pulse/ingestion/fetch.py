"""Pull daily OHLCV history for one ticker and land it as raw (bronze) Parquet."""

import pandas as pd
import yfinance as yf

from b3_pulse.config import settings


def fetch_history(ticker: str, start_date: str, end_date: str | None) -> pd.DataFrame:
    df = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False, progress=False)
    if df.empty:
        raise ValueError(f"yfinance returned no rows for {ticker!r} in [{start_date}, {end_date}]")

    df.columns = df.columns.get_level_values(0) if df.columns.nlevels > 1 else df.columns
    df = df.reset_index().rename(columns=str.lower)
    df["ticker"] = ticker
    df["dt"] = df["date"].dt.strftime("%Y-%m-%d")
    return df


def write_bronze(df: pd.DataFrame, ticker: str) -> list[str]:
    storage_options = {
        "key": settings.minio_access_key,
        "secret": settings.minio_secret_key,
        "client_kwargs": {"endpoint_url": settings.minio_endpoint},
    }
    written = []
    for dt, day_df in df.groupby("dt"):
        path = f"s3://{settings.bronze_bucket}/{ticker}/dt={dt}/data.parquet"
        day_df.to_parquet(path, index=False, storage_options=storage_options)
        written.append(path)
    return written


def run(
    ticker: str | None = None, start_date: str | None = None, end_date: str | None = None
) -> list[str]:
    ticker = ticker or settings.ticker
    start_date = start_date or settings.start_date
    end_date = end_date or settings.end_date
    df = fetch_history(ticker, start_date, end_date)
    return write_bronze(df, ticker)


if __name__ == "__main__":
    paths = run()
    print(f"Wrote {len(paths)} daily partitions to bronze.")
