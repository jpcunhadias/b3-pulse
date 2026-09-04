from b3_pulse.config import settings
from b3_pulse.ingestion.fetch import run as ingest
from b3_pulse.transform.catalog import register_refined_quotes
from b3_pulse.transform.refine import refine


def main() -> None:
    print(f"Ingesting {settings.ticker} into bronze...")
    paths = ingest()
    print(f"  wrote {len(paths)} daily partitions")

    print("Refining bronze -> silver...")
    refine(settings.ticker)

    print("Registering warehouse.refined_quotes...")
    warehouse = register_refined_quotes()
    print(f"Done. Query it with DuckDB against {warehouse}")
