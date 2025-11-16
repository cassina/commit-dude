import logging
import re
import time
from importlib import resources
from importlib.abc import Traversable
from pathlib import Path
from typing import List, Optional, Union

import yaml

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import hook_config
from langchain_core.messages import BaseMessage
from langgraph.runtime import Runtime

from commit_dude.core.config import REDACTION
from commit_dude.core.settings import commit_dude_logger
from commit_dude.core.errors import SecretPatternDetectorError
from commit_dude.core.schemas import Strategy


class SecretPatternDetectorMiddleware(AgentMiddleware):
    state_schema = AgentState

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        patterns_yaml_path: Optional[Union[str, Path, Traversable]] = None,
        confidence_threshold: float = 0.5,
        strategy: Strategy = "block",
    ):
        self._logger = logger or commit_dude_logger(__name__)
        self.strategy = strategy
        self.patterns = self._load_patterns(patterns_yaml_path)
        self.compiled = self._compile_patterns(self.patterns, confidence_threshold)

    def _default_patterns_path(self) -> Traversable:
        return resources.files("commit_dude.core.files").joinpath("rules-stable.yml")

    def _load_patterns(self, yaml_path: Optional[Union[str, Path, Traversable]]):
        pattern_path: Traversable
        if yaml_path:
            pattern_path = Path(yaml_path)
        else:
            pattern_path = self._default_patterns_path()

        with pattern_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("patterns", [])

    def _compile_patterns(self, entries, threshold):
        compiled = []
        confidence_map = {"low": 0.1, "medium": 0.5, "high": 0.9}

        for e in entries:
            p = e.get("pattern", {})
            pid = p.get("name", "<unknown>")
            regex = p.get("regex")
            confidence = confidence_map.get(p.get("confidence", "low"), 0)

            if not regex or confidence < threshold:
                continue

            try:
                compiled.append((pid, re.compile(regex)))
            except re.error as err:
                self._logger.warning(f"Bad regex for {pid}: {err}")

        return compiled

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: AgentState, runtime: Runtime):
        start_time = time.perf_counter()
        self._logger.debug("Checking for secret patterns...")
        text_parts = []

        # Collect messages (We only have 1 message per call)
        for msg in state["messages"]:
            c = getattr(msg, "content", "")
            if isinstance(c, str):
                text_parts.append(c)

        text = " ".join(text_parts)

        # Detect patterns
        matches = []
        for pid, regex in self.compiled:
            for m in regex.finditer(text):
                matches.append((pid, m.group(0)))

        if not matches:
            self._logger.debug("No secret patterns detected.")
            self._logger.debug(
                "Finished secret pattern detection in %.2f ms.",
                (time.perf_counter() - start_time) * 1000,
            )
            return None

        self._logger.warning(f"Secret patterns detected. Strategy: {self.strategy}")
        # 🚨 BLOCK MODE: hard stop
        if self.strategy == "block":
            self._logger.debug(
                "Secret pattern detection completed in %.2f ms before blocking.",
                (time.perf_counter() - start_time) * 1000,
            )
            raise SecretPatternDetectorError(
                f"Secret pattern detected: {matches[0][0]}"
            )

        # 🛡️ REDACT MODE: continue, but sanitize messages
        self._logger.warning("Redacting secret patterns detected...")
        replaced_count = 0
        if self.strategy == "redact":
            new_messages: List[BaseMessage] = []
            for msg in state["messages"]:
                content = getattr(msg, "content", "")

                if isinstance(content, str):
                    for _, detected in matches:
                        content = content.replace(detected, REDACTION)
                        replaced_count += 1
                    msg = msg.model_copy(update={"content": content})

                new_messages.append(msg)

            self._logger.warning(
                f"Finished secret pattern detection. Replaced {replaced_count} patterns."
            )
            self._logger.debug(
                "Finished secret pattern detection after %.2f ms",
                (time.perf_counter() - start_time) * 1000,
            )
            return {"messages": [*new_messages]}
        return None
