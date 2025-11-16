import logging
from typing import Any, Optional

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_openai import ChatOpenAI
from langgraph.runtime import Runtime

from commit_dude.core.settings import commit_dude_logger
from commit_dude.core.config import MAX_TOKENS
from commit_dude.core.errors import TokenLimitExceededError


class TokenCountMiddleware(AgentMiddleware):
    state_schema = AgentState

    def __init__(
            self,
            model: ChatOpenAI,
            logger: Optional[logging.Logger] = None,
    ):
        self._logger = logger or commit_dude_logger(__name__)
        self._model = model
        self._max_tokens = MAX_TOKENS

    def _validate_num_tokens(self, diff: str) -> int:
            self._logger.debug("Validating approximate token count for diff")

            num_tokens = self._model.get_num_tokens(diff)
            self._logger.debug(
                "Diff token count: %d (max allowed: %d)", num_tokens, self._max_tokens
            )

            if num_tokens > self._max_tokens:
                error_msg = (
                    f"Diff is too long. Max tokens: {self._max_tokens}, "
                    f"diff tokens: {num_tokens}"
                )
                self._logger.error(error_msg)
                raise TokenLimitExceededError(error_msg)

            self._logger.debug("Token count validation passed")
            return num_tokens

    def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        messages = state.get("messages")

        # Find the last HumanMessage
        human_message = None
        for msg in reversed(messages):
            if msg.type == "human":
                human_message = msg
                break

        # Extract text content
        content = human_message.content
        if not isinstance(content, str):
            raise ValueError("Human message content must be a string")

        self._validate_num_tokens(content)

        # No state modifications required
        return None


