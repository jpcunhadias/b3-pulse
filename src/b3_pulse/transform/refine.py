"""Bronze -> silver refinement: the required aggregate / rename / date-calc trio.

Mirrors the original Glue-visual job's three mandatory transformations, just
expressed as SQL instead of a no-code canvas:
  A. numeric aggregation (sum/avg/count grouped by ticker + trading day)
  B. renaming two non-grouping columns
  C. a date calculation (gap in days since the previous trading session)
"""

from b3_pulse.lake import bronze_path, connect, silver_root

REFINE_SQL = """
with bronze as (
    select * from {bronze_source}
),
aggregated as (
    select
        ticker,
        dt,
        cast(dt as date) as trade_date,
        max(high) as high,
        min(low) as low,
        first(open order by date) as open,
        last(close order by date) as closing_price,   -- B: renamed from `close`
        sum(volume) as trade_volume                    -- A + B: aggregated & renamed from `volume`
    from bronze
    group by ticker, dt
)
select
    *,
    date_diff(
        'day',
        lag(trade_date) over (partition by ticker order by trade_date),
        trade_date
    ) as days_since_last_session                        -- C: date calculation
from aggregated
"""


def refine(ticker: str) -> str:
    con = connect()
    bronze_source = f"read_parquet('{bronze_path(ticker)}', hive_partitioning = true)"
    sql = REFINE_SQL.format(bronze_source=bronze_source)
    dest = silver_root()
    con.execute(f"""
        copy ({sql})
        to '{dest}'
        (format parquet, partition_by (ticker, dt), overwrite_or_ignore 1)
    """)
    return dest


if __name__ == "__main__":
    from b3_pulse.config import settings

    path = refine(settings.ticker)
    print(f"Refined silver data written under {path}")
