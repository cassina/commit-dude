"""Project logging configuration utilities."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Final


_DEFAULT_FORMAT: Final[str] = "%(message)s"
_RESET: Final[str] = "\033[0m"
_BOLD: Final[str] = "\033[1m"
_DIM: Final[str] = "\033[2m"


def _rgb_escape(red: int, green: int, blue: int) -> str:
    """Return the ANSI escape sequence for a 24-bit foreground color."""

    return f"\033[38;2;{red};{green};{blue}m"


@dataclass(frozen=True)
class _LevelStyle:
    """Styling information for a log level."""

    label: str
    color: str
    bold: bool = False
    dim: bool = False

    def render(self, message: str) -> str:
        """Decorate *message* with the configured ANSI styles."""

        prefix = f"[{self.label}]"
        modifiers: list[str] = []

        if self.bold:
            modifiers.append(_BOLD)
        if self.dim:
            modifiers.append(_DIM)

        modifiers.append(self.color)

        return f"{''.join(modifiers)}{prefix} {message}{_RESET}"


_LEVEL_STYLES: Final[dict[int, _LevelStyle]] = {
    logging.DEBUG: _LevelStyle("DEBUG", _rgb_escape(110, 246, 223), dim=True),
    logging.INFO: _LevelStyle("INFO", _rgb_escape(118, 245, 249)),
    logging.WARNING: _LevelStyle(
        "WARNING",
        _rgb_escape(193, 255, 185),
        bold=True,
    ),
    logging.ERROR: _LevelStyle(
        "ERROR",
        _rgb_escape(229, 136, 224),
        bold=True,
    ),
    logging.CRITICAL: _LevelStyle(
        "CRITICAL",
        _rgb_escape(165, 142, 238),
        bold=True,
    ),
}


class _ColorFormatter(logging.Formatter):
    """Formatter that adds Commit Dude's colorful log prefixes."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)

        style = _LEVEL_STYLES.get(record.levelno)
        if not style:
            return message

        return style.render(message)


def _parse_level_from_env() -> int | None:
    """Return the log level defined in the environment, if any."""

    level_name = os.getenv("COMMIT_DUDE_LOG_LEVEL")
    if not level_name:
        return None

    return getattr(logging, level_name.upper(), None)


def commit_dude_logger(name: str) -> logging.Logger:
    """Return a pre-configured logger with Commit Dude's signature styling."""

    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_ColorFormatter(_DEFAULT_FORMAT))
        handler.setLevel(logging.NOTSET)
        logger.addHandler(handler)

    level = _parse_level_from_env()
    logger.setLevel(level if level is not None else logging.NOTSET)

    return logger
