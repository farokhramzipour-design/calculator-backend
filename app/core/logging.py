from __future__ import annotations

import logging
import structlog


def configure_logging() -> None:
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
    )


def get_logger():
    return structlog.get_logger()
