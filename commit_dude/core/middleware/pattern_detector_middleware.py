import logging
import time
from typing import List, Optional

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import hook_config
from langchain_core.messages import BaseMessage
from langgraph.runtime import Runtime

from commit_dude.core.config import REDACTION
from commit_dude.core.settings import commit_dude_logger
from commit_dude.core.errors import SecretPatternDetectorError
from commit_dude.core.schemas import Strategy
from commit_dude.core.yaml_loader import YAMLLoader


class SecretPatternDetectorMiddleware(AgentMiddleware):
    state_schema = AgentState

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        yaml_loader: Optional[YAMLLoader] = None,
        confidence_threshold: float = 0.5,
        strategy: Strategy = "block",
    ):
        self._logger = logger or commit_dude_logger(__name__)
        self.strategy = strategy

        self._logger.debug("Initializing secret pattern detector middleware...")

        if not yaml_loader:
            self.yaml_loader = YAMLLoader()
        self.compiled = self.yaml_loader.load_and_compile(confidence_threshold)

        self._logger.debug("Compiled patterns, confidence threshold: %s", confidence_threshold)

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
        matches = self._detect(text)
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

    def _detect(self, text):
        matches = []
        for pid, regex in self.compiled:
            for m in regex.finditer(text):
                matches.append((pid, m.group(0)))
        return matches