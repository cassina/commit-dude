import logging
import textwrap
from typing import List, Optional

from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from commit_dude.config import SYSTEM_PROMPT
from commit_dude.schemas import CommitMessageResponse
from commit_dude.settings import commit_dude_logger
from commit_dude.config import MAX_TOKENS
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
        self._model = ChatOpenAI(model=model_name, temperature=0.5)
        self._agent = create_agent(
            model=self._model,
            system_prompt=SYSTEM_PROMPT,
            response_format=ProviderStrategy(CommitMessageResponse),
            middleware=[
                SecretPatternDetectorMiddleware(
                    strategy=f"{'block' if strict else 'redact'}"
                )
            ],
        )
        self._strict = strict

    def invoke(self, diff: str):
        self._logger.debug("Starting diff processing")

        # Validate approximate token count
        self._validate_num_tokens(diff)

        self._logger.debug("Starting commit message generation")
        result = self._agent.invoke({"messages": [HumanMessage(content=diff)]})
        structured_response: CommitMessageResponse = result["structured_response"]
        structured_response.commit_message = self._wrap_commit_message(
            structured_response.commit_message
        )
        result["structured_response"] = structured_response

        self._logger.debug("Commit message generation completed successfully")
        return result

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

    def _wrap_commit_message(self, commit_message: str) -> str:
        """Wrap each paragraph to ensure no line exceeds 100 characters."""

        if not commit_message:
            return commit_message

        wrapped_lines: List[str] = []
        for paragraph in self._split_paragraphs(commit_message):
            if paragraph == "":
                wrapped_lines.append("")
                continue

            bullet_prefix = ""
            body = paragraph
            for prefix in ("- ", "* ", "+ "):
                if paragraph.startswith(prefix):
                    bullet_prefix = prefix
                    body = paragraph[len(prefix) :].strip()
                    break

            if bullet_prefix:
                wrapped = textwrap.wrap(
                    body,
                    width=100,
                    initial_indent=bullet_prefix,
                    subsequent_indent=" " * len(bullet_prefix),
                )
            else:
                wrapped = textwrap.wrap(paragraph, width=100)

            wrapped_lines.extend(wrapped or [""])

        return "\n".join(wrapped_lines)

    def _split_paragraphs(self, commit_message: str) -> List[str]:
        paragraphs: List[str] = []
        if commit_message is None:
            return paragraphs

        current_lines: List[str] = []
        for line in commit_message.splitlines():
            if not line.strip():
                if current_lines:
                    paragraphs.append(" ".join(current_lines).strip())
                    current_lines = []
                paragraphs.append("")
                continue

            current_lines.append(line.strip())

        if current_lines:
            paragraphs.append(" ".join(current_lines).strip())

        return paragraphs


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
