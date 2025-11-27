from __future__ import annotations

import logging
from importlib import resources
from importlib.abc import Traversable
from typing import Optional

import yaml

from commit_dude.core.settings import commit_dude_logger

PATTERNS_PATH = resources.files("commit_dude.core.files").joinpath("rules-stable.yml")


class YAMLLoader:
    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        patterns_yaml_path: Traversable = PATTERNS_PATH,
    ):
        self._logger = logger or commit_dude_logger(__name__)
        self._patterns_yaml_path = patterns_yaml_path

    def load_patterns(self, yaml_path: Optional[Traversable] = None) -> list:
        target_path = yaml_path or self._patterns_yaml_path
        if not target_path.name.endswith((".yml", ".yaml")):
            self._logger.error("Invalid patterns file extension: %s", target_path)
            raise yaml.YAMLError(f"Invalid patterns file: {target_path}")

        try:
            with target_path.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
        except FileNotFoundError:
            self._logger.error("Patterns file not found: %s", target_path)
            raise
        except yaml.YAMLError:
            self._logger.error("Unable to parse patterns YAML: %s", target_path)
            raise

        patterns = data.get("patterns", [])
        if not isinstance(patterns, list):
            self._logger.warning("Patterns entry is not a list in %s", target_path)
            return []

        self._logger.debug("Loaded %d patterns from %s", len(patterns), target_path)
        return patterns
