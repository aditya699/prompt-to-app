"""One place to configure logging for the whole server."""

from __future__ import annotations

import logging


def configure_logging(level: str = "INFO") -> None:
    """Set a readable format on the root logger. Call once at startup."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # httpx logs every request at INFO, which drowns out the app during ingestion.
    logging.getLogger("httpx").setLevel(logging.WARNING)
