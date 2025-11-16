import logging
import time
from typing import Any, Optional

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime

from commit_dude.utils import wrap_commit_message
from commit_dude.core.schemas import CommitMessageResponse
from commit_dude.core.settings import commit_dude_logger


class CommitLengthMiddleware(AgentMiddleware):
    state_schema = AgentState

    def __init__(
            self,
            logger: Optional[logging.Logger] = None,
            strict: bool = True,
    ):
        self._logger = logger or commit_dude_logger(__name__)
        self._strict = strict

    def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        start_time = time.perf_counter()
        self._logger.debug("After model: wrapping commit message lines...")

        structured = state["structured_response"]
        if not isinstance(structured, CommitMessageResponse):
            raise ValueError("Structured response not found or invalid type")

        # wrap the commit message
        wrapped_message = wrap_commit_message(structured.commit_message)
        self._logger.debug(
            "Finished wrapping commit message in %.2f ms",
            (time.perf_counter() - start_time) * 1000
        )

        # new structured response
        updated = CommitMessageResponse(
            agent_response=structured.agent_response,
            commit_message=wrapped_message
        )

        # IMPORTANT: return *partial* state
        return {
            "structured_response": updated
        }
