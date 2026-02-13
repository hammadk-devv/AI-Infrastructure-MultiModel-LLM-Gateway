from __future__ import annotations

import logging
import sys
from typing import Any


def configure_logging(json: bool) -> None:
    """Configure application-wide logging.

    Args:
        json: Whether to emit JSON-formatted logs.
    """

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler: logging.Handler
    if json:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt='{"level":"%(levelname)s","time":"%(asctime)s","name":"%(name)s",'
            '"message":"%(message)s","extra":%(lkg_extra)s}',
        )
    else:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger with default extra field support."""

    logger = logging.getLogger(name)

    def _log_with_extra(
        level: int,
        msg: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        extra = kwargs.pop("extra", {}) or {}
        if "lkg_extra" not in extra:
            extra["lkg_extra"] = "{}"
        logger.log(level, msg, *args, extra=extra, **kwargs)

    logger.log_with_extra = _log_with_extra  # type: ignore[attr-defined]
    return logger

