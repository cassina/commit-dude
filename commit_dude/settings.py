"""Project logging configuration utilities."""

from __future__ import annotations

import logging
import os
from typing import Final


_DEFAULT_FORMAT: Final[str] = "%(message)s"


def _parse_level_from_env() -> int | None:
    """Return the log level defined in the environment, if any."""

    level_name = os.getenv("COMMIT_DUDE_LOG_LEVEL")
    if not level_name:
        return None

    return getattr(logging, level_name.upper(), None)


def commit_dude_logger(name: str) -> logging.Logger:
    """Return a lightweight, pre-configured logger for the project."""

    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
        handler.setLevel(logging.NOTSET)
        logger.addHandler(handler)

    level = _parse_level_from_env()
    logger.setLevel(level if level is not None else logging.NOTSET)

    return logger
