from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from importlib import resources
from importlib.abc import Traversable
from typing import Optional

import yaml

from commit_dude.core.settings import commit_dude_logger

PATTERNS_PATH = resources.files("commit_dude.core.files").joinpath("rules-stable.yml")
SIGNATURE_KEY_ENV = "COMMIT_DUDE_PATTERNS_KEY"
SIGNATURE_SALT_ENV = "COMMIT_DUDE_PATTERNS_SALT"
SIGNATURE_OVERRIDE_ENV = "COMMIT_DUDE_PATTERNS_SIGNATURE_OVERRIDE"


class YAMLLoader:
    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        patterns_yaml_path: Traversable = PATTERNS_PATH,
    ):
        self._logger = logger or commit_dude_logger(__name__)
        self._patterns_yaml_path = patterns_yaml_path
        self._signature_key = os.getenv(SIGNATURE_KEY_ENV, "")
        self._signature_salt = os.getenv(SIGNATURE_SALT_ENV, "")
        self._signature_override = os.getenv(SIGNATURE_OVERRIDE_ENV)

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

        signature = data.get("signature")
        if not signature:
            self._logger.error("Patterns file missing signature: %s", target_path)
            raise yaml.YAMLError(f"Missing signature in patterns file: {target_path}")

        if not self._validate_signature(data, signature):
            self._logger.error("Signature validation failed for patterns file: %s", target_path)
            raise yaml.YAMLError(f"Invalid signature for patterns file: {target_path}")

        patterns = data.get("patterns", [])
        if not isinstance(patterns, list):
            self._logger.warning("Patterns entry is not a list in %s", target_path)
            return []

        self._logger.debug("Loaded %d patterns from %s", len(patterns), target_path)
        return patterns

    def _validate_signature(self, data: dict, provided_signature: str) -> bool:
        payload = {key: value for key, value in data.items() if key != "signature"}
        expected_signature = self._signature_override or self._generate_signature(payload)

        if not expected_signature:
            self._logger.warning("Signature key and salt are required to validate patterns files.")
            return False

        return hmac.compare_digest(provided_signature, expected_signature)

    def _generate_signature(self, payload: dict) -> str:
        if not self._signature_key or not self._signature_salt:
            return ""

        normalized_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        message = f"{self._signature_salt}:{normalized_payload}"
        digest = hmac.new(
            key=self._signature_key.encode("utf-8"),
            msg=message.encode("utf-8"),
            digestmod=hashlib.sha256,
        )
        return digest.hexdigest()
