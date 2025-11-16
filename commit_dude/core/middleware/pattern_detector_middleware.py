import re
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, List, Union, Literal, Optional

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import hook_config
from langchain_core.messages import BaseMessage

from commit_dude.settings import commit_dude_logger
from commit_dude.errors import SecretPatternDetectorError
from commit_dude.config import REDACTION


class SecretPatternDetectorMiddleware(AgentMiddleware):
    state_schema = AgentState

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        patterns_yaml_path: Union[
            str, Path
        ] = "commit_dude/core/files/rules-stable.yml",
        confidence_threshold: float = 0.5,
        strategy: Literal["block", "redact"] = "block",
    ):
        self._logger = logger or commit_dude_logger(__name__)
        self.strategy = strategy
        self.patterns = self._load_patterns(patterns_yaml_path)
        self.compiled = self._compile_patterns(self.patterns, confidence_threshold)

    def _log_completion(self, start_time: datetime, message: str = "") -> None:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        completion_message = f"Secret pattern detection finished at {end_time.isoformat()} (duration: {duration:.4f}s)."
        if message:
            completion_message = f"{completion_message} {message}"
        self._logger.debug(completion_message)

    def _load_patterns(self, yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
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
    def before_model(self, state: AgentState, runtime: Any):
        start_time = datetime.utcnow()
        self._logger.debug(
            f"Secret pattern detection started at {start_time.isoformat()}. Checking for secret patterns..."
        )
        text_parts = []

        # Collect messages
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
            self._log_completion(start_time, "Generating commit message...")
            return None
        else:
            self._logger.warning(f"Secret patterns detected. Strategy: {self.strategy}")
            # 🚨 BLOCK MODE: hard stop
            if self.strategy == "block":
                self._log_completion(start_time, "Blocking commit message generation.")

                raise SecretPatternDetectorError(
                    f"Secret pattern detected: {matches[0][0]}"
                )

            else:
                # 🛡️ REDACT MODE: continue, but sanitize messages
                self._logger.warning("Redacting secret patterns detected...")
                replaced_count = 0

                new_messages: List[BaseMessage] = []
                for msg in state["messages"]:
                    content = getattr(msg, "content", "")

                    if isinstance(content, str):
                        for _, detected in matches:
                            content = content.replace(detected, REDACTION)
                            replaced_count += 1
                        msg = msg.model_copy(update={"content": content})

                    new_messages.append(msg)

                self._logger.warning(f"Finished secret pattern detection. Replaced {replaced_count} patterns.")
                self._log_completion(start_time, "Generating commit message...")
                return {
                    "messages": [
                        *new_messages
                    ]
                }
        # return None
