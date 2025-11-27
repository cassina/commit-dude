import logging
from typing import Any

from langchain_ollama import ChatOllama
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult

from commit_dude.core.settings import commit_dude_logger


class LocalCommitModel(BaseChatModel):
    """Thin wrapper around :class:`ChatOllama` with sensible defaults."""

    def __init__(
        self,
        *,
        model: str = "llama3.2",
        base_url: str | None = None,
        temperature: float = 0.3,
        max_new_tokens: int = 512,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__()
        self._logger = logger or commit_dude_logger(__name__)
        self._max_new_tokens = max_new_tokens
        self._client = ChatOllama(
            model=model,
            base_url=base_url,
            temperature=temperature,
            num_predict=max_new_tokens,
        )

        self._logger.info(
            "Initialized Ollama model '%s' (base_url=%s, max_new_tokens=%d)",
            model,
            base_url,
            max_new_tokens,
        )

    @property
    def _llm_type(self) -> str:  # pragma: no cover - required by BaseLLM
        return "ollama-commit-model"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return self._client._generate(
            messages=messages, stop=stop, run_manager=run_manager, **kwargs
        )

    def get_num_tokens(self, text: str) -> int:
        """Use Ollama's tokenizer via the underlying client."""

        return self._client.get_num_tokens(text)
