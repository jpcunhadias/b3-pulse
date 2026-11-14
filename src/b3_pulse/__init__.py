import logging

from b3_pulse.config import settings
from b3_pulse.features.build import build_features
from b3_pulse.ingestion.fetch import run as ingest
from b3_pulse.logging_config import configure_logging
from b3_pulse.transform.catalog import register_features, register_refined_quotes
from b3_pulse.transform.refine import refine

logger = logging.getLogger(__name__)


def main() -> None:
    configure_logging()

    logger.info("Ingesting %s into bronze...", settings.ticker)
    paths = ingest()
    logger.info("Wrote %d daily partitions", len(paths))

    logger.info("Refining bronze -> silver...")
    refine(settings.ticker)
    register_refined_quotes()

    logger.info("Building features (silver -> gold)...")
    build_features(settings.ticker)
    warehouse = register_features()

    logger.info("Done. Query warehouse.refined_quotes / warehouse.features in %s", warehouse)
