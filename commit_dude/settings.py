"""Project logging configuration utilities."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Final


_REGISTERED_LOGGERS: set[logging.Logger] = set()


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

    def render(self, message: str, logger_name: str) -> str:
        """Decorate *message* with the configured ANSI styles."""

        prefix = f"[🐛 {self.label}::{logger_name}]"
        modifiers: list[str] = []

        if self.bold:
            modifiers.append(_BOLD)
        if self.dim:
            modifiers.append(_DIM)

        modifiers.append(self.color)

        return f"{''.join(modifiers)}{prefix} {message}{_RESET}"


_LEVEL_STYLES: Final[dict[int, _LevelStyle]] = {
    logging.DEBUG: _LevelStyle("DEBUG", _rgb_escape(110, 246, 223), dim=True),
    logging.INFO: _LevelStyle("INFO", _rgb_escape(91, 203, 255)),
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

        # Pass logger name to the style renderer
        return style.render(message, record.name)



def _parse_level_from_env() -> int | None:
    """Return the log level defined in the environment, if any."""

    level_name = os.getenv("COMMIT_DUDE_LOG_LEVEL")
    if not level_name:
        return None

    return getattr(logging, level_name.upper(), None)


def _effective_level() -> int:
    """Return the currently configured log level or NOTSET when undefined."""

    level = _parse_level_from_env()
    return level if level is not None else logging.NOTSET


def _register(logger: logging.Logger) -> None:
    """Keep track of configured loggers for later reconfiguration."""

    _REGISTERED_LOGGERS.add(logger)


def commit_dude_logger(name: str) -> logging.Logger:
    """Return a pre-configured logger with Commit Dude's signature styling."""

    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_ColorFormatter(_DEFAULT_FORMAT))
        handler.setLevel(logging.NOTSET)
        logger.addHandler(handler)

    env_level = _parse_level_from_env()
    if env_level is not None:
        logger.setLevel(env_level)
    _register(logger)

    return logger


def set_commit_dude_log_level(level_name: str) -> None:
    """Set the log level for all Commit Dude loggers."""

    os.environ["COMMIT_DUDE_LOG_LEVEL"] = level_name
    level = _effective_level()

    for logger in _REGISTERED_LOGGERS:
        logger.setLevel(level)
