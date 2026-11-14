import logging

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the root logger. Call once per entrypoint, never at import time."""
    logging.basicConfig(level=level, format=LOG_FORMAT)
