import logging
from typing import Optional, Dict, Any, Sequence

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain.agents.structured_output import ProviderStrategy

from commit_dude.config import MAX_TOKENS
from commit_dude.config import SYSTEM_PROMPT
from commit_dude.utils import wrap_commit_message
from commit_dude.settings import commit_dude_logger
from commit_dude.schemas import CommitMessageResponse, Strategy
from commit_dude.errors import TokenLimitExceededError
from commit_dude.core.middleware import SecretPatternDetectorMiddleware


class CommitDudeAgent:
    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        model_name: str = "gpt-5-mini",
        # model_name: str = "gpt-4o-mini",
        strict: bool = True,
    ) -> None:
        self._logger = logger or commit_dude_logger(__name__)
        self._max_tokens = MAX_TOKENS
        self._strict = strict
        self._strategy: Strategy = "block" if strict else "redact"

        # Set Agent configuration
        self._model = ChatOpenAI(model=model_name, temperature=0.5)
        self._middleware: Sequence[Any] = [
            SecretPatternDetectorMiddleware(strategy=self._strategy),
        ]

        # Create Agent
        self._agent = create_agent(
            model=self._model,
            system_prompt=SYSTEM_PROMPT,
            response_format=ProviderStrategy(CommitMessageResponse),
            middleware=self._middleware,
        )

    def invoke(self, diff: str) -> dict:
        self._logger.debug("Starting diff processing")

        # Validate approximate token count
        self._validate_num_tokens(diff)

        self._logger.debug("Starting commit message generation")

        # --- Agent call ---
        try:
            result: Dict[str, Any] = self._agent.invoke(
                {"messages": [HumanMessage(content=diff)]}
            )
        except Exception as exc:
            self._logger.error("Agent invocation failed: %s", exc)
            raise

        # --- Validate structured response ---
        structured = result.get("structured_response")
        if structured is None:
            raise RuntimeError("Agent did not return a 'structured_response' key.")
        if not isinstance(structured, CommitMessageResponse):
            raise TypeError(
                f"'structured_response' must be CommitMessageResponse, got {type(structured)}"
            )

        # --- Cleanup / postprocess ---
        cleaned_message = self._ensure_commit_message_length(structured.commit_message)
        new_response = structured.model_copy(update={"commit_message": cleaned_message})

        self._logger.debug("Commit message generation completed successfully")

        # Return a NEW dict to avoid side effects
        return {**result, "structured_response": new_response}

    def _validate_num_tokens(self, diff: str) -> int:
        self._logger.debug("Validating token count for diff")

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

    @staticmethod
    def _ensure_commit_message_length(commit_message: str) -> str:
        return wrap_commit_message(commit_message=commit_message)


if __name__ == "__main__":
    agent = CommitDudeAgent(strict=False)
    msg = (
        "diff --git a/commit_dude/config.py b/commit_dude/config.py "
        "index eff3b66..71898b1 100644 --- a/commit_dude/config.py +++ b/commit_dude/config.py "
        "-SYSTEM_PROMPT = You are Git Commit Dude with a laid back and relaxed attitude, always chilling."
        "+SYSTEM_PROMPT = +You are Git Commit Dude, a conventional commit generator, with a laid back and relaxed attitude, always chilling.\n"
        "+F = 'FFF'"
    )

    response = agent.invoke(msg)
    print(f"Response: {response['messages'][-1].content}")
