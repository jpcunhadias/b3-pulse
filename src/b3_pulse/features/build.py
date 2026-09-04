"""Silver -> features (gold): engineer model-ready features from refined quotes.

Every feature is computed purely from past values (window frames look
backward, `lag`/no forward peeking) except `target_next_close`, which is
deliberately the one forward-looking column — the supervised label for the
baseline model and, later, the LSTM.
"""

from b3_pulse.lake import connect, features_root, silver_glob

FEATURES_SQL = """
with silver as (
    select * from {silver_source}
)
select
    ticker,
    dt,
    trade_date,
    closing_price,
    trade_volume,
    (closing_price / lag(closing_price) over w) - 1
        as daily_return,
    avg(closing_price) over (
        partition by ticker order by trade_date
        rows between 4 preceding and current row
    ) as ma_5,
    avg(closing_price) over (
        partition by ticker order by trade_date
        rows between 9 preceding and current row
    ) as ma_10,
    stddev_samp(closing_price) over (
        partition by ticker order by trade_date
        rows between 4 preceding and current row
    ) as volatility_5,
    lead(closing_price) over w as target_next_close
from silver
window w as (partition by ticker order by trade_date)
"""


def build_features(ticker: str) -> str:
    con = connect()
    silver_source = f"""(
        select * from read_parquet('{silver_glob()}', hive_partitioning = true)
        where ticker = '{ticker}'
    )"""
    sql = FEATURES_SQL.format(silver_source=silver_source)
    dest = features_root()
    con.execute(f"""
        copy ({sql})
        to '{dest}'
        (format parquet, partition_by (ticker, dt), overwrite_or_ignore 1)
    """)
    return dest


if __name__ == "__main__":
    from b3_pulse.config import settings

    path = build_features(settings.ticker)
    print(f"Features written under {path}")
