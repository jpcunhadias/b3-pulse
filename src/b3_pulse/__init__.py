from b3_pulse.config import settings
from b3_pulse.features.build import build_features
from b3_pulse.ingestion.fetch import run as ingest
from b3_pulse.transform.catalog import register_features, register_refined_quotes
from b3_pulse.transform.refine import refine


def main() -> None:
    print(f"Ingesting {settings.ticker} into bronze...")
    paths = ingest()
    print(f"  wrote {len(paths)} daily partitions")

    print("Refining bronze -> silver...")
    refine(settings.ticker)
    register_refined_quotes()

    print("Building features (silver -> gold)...")
    build_features(settings.ticker)
    warehouse = register_features()

    print(f"Done. Query warehouse.refined_quotes / warehouse.features in {warehouse}")
