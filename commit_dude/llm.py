#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module for managing commit message generation using OpenAI's LLM."""

import os
from typing import List, Type, Optional, Union, Callable

from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.runnables import Runnable
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage

from commit_dude.schemas import CommitMessageResponse
from commit_dude.config import SYSTEM_PROMPT, MAX_TOKENS
from commit_dude.settings import commit_dude_logger
from commit_dude.errors import TokenLimitExceededError, ApiKeyMissingError

# Load .env automatically
load_dotenv()
# Setup logger
logger = commit_dude_logger(__name__)


class ChatCommitDude:
    """Manage commit message generation.

    This class handles the generation of commit messages from Git diffs
    using language models with structured output.

    Attributes:
        model (str): The OpenAI model name to use.
        output (Type[BaseModel]): The output schema for structured responses.
        max_tokens (int): Maximum allowed tokens for input diff.
        llm (BaseChatModel): The language model instance.
        structured_llm (Runnable): The structured output language model.
    """

    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_TEMPERATURE = 0.2

    # --- Initialization ---
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        output: Type[BaseModel] = CommitMessageResponse,
        llm: Optional[Union[ChatOpenAI, BaseChatModel]] = None,
        structured_llm: Optional[Runnable] = None,
        get_env: Callable[[str], Optional[str]] = os.getenv,
        max_tokens: int = MAX_TOKENS,
        validate_api_key: bool = True,
    ) -> None:
        """Initialize ChatCommitDude with configuration and dependencies.

        Args:
            model: OpenAI model name to use.
            output: Pydantic model class for structured output.
            llm: Pre-configured language model instance.
            structured_llm: Pre-configured structured output runnable.
            get_env: Function to retrieve environment variables.
            max_tokens: Maximum allowed tokens for input diff.
            validate_api_key: Whether to validate API key during initialization.

        Raises:
            ApiKeyMissingError: If OPENAI_API_KEY is not found and validation enabled.
        """
        logger.debug("Initializing ChatCommitDude with model: %s", model)

        self.model = model
        self.output = output
        self._get_env = get_env
        self.max_tokens = max_tokens

        if validate_api_key:
            self._validate_api_key()

        # Use injected dependencies or create defaults
        self.llm = llm or self._build_model()
        self.structured_llm = structured_llm or self._build_structured_llm()

    # --- Public methods ---
    def invoke(self, diff: str) -> CommitMessageResponse:
        """Generate a commit message with validation and error handling.

        Args:
            diff: Git diff content.

        Returns:
            CommitMessageResponse with generated commit message.

        Raises:
            TokenLimitExceededError: If diff exceeds token limit.
            Exception: If commit message generation fails.
        """
        logger.debug("Starting commit message generation")
        logger.debug("Diff length: %d characters", len(diff))

        self._validate_num_tokens(diff)
        result = self._generate_commit_message(diff)

        logger.debug("Commit message generation completed successfully")
        return result

    # --- Private methods ---
    def _validate_num_tokens(self, diff: str) -> int:
        """Validate that diff doesn't exceed token limit.

        Args:
            diff: Git diff content to validate.

        Returns:
            Number of tokens in the diff.

        Raises:
            TokenLimitExceededError: If diff exceeds maximum token limit.
        """
        logger.debug("Validating token count for diff")

        num_tokens = self.llm.get_num_tokens(diff)
        logger.debug(
            "Diff token count: %d (max allowed: %d)", num_tokens, self.max_tokens
        )

        if num_tokens > self.max_tokens:
            error_msg = (
                f"Diff is too long. Max tokens: {self.max_tokens}, "
                f"diff tokens: {num_tokens}"
            )
            logger.error(error_msg)
            raise TokenLimitExceededError(error_msg)

        logger.debug("Token count validation passed")
        return num_tokens

    def _generate_commit_message(self, diff: str) -> CommitMessageResponse:
        """Generate commit message from Git diff.

        Args:
            diff: Git diff content.

        Returns:
            CommitMessageResponse with generated commit message.

        Raises:
            Exception: If LLM invocation fails.
        """
        logger.debug("Generating commit message from diff via structured LLM")

        messages = self._build_messages(diff)

        try:
            result = self.structured_llm.invoke(messages)
            logger.debug("Successfully generated commit message")
            return result
        except Exception as e:
            logger.error("Failed to generate commit message: %s", str(e), exc_info=True)
            raise

    def _build_model(self) -> ChatOpenAI:
        """Build ChatOpenAI model instance.

        Returns:
            Configured ChatOpenAI instance.
        """
        logger.debug("Building ChatOpenAI model with name: %s", self.model)

        llm = ChatOpenAI(model=self.model, temperature=self.DEFAULT_TEMPERATURE)
        logger.debug(
            "Using LLM: %s with temperature: %.1f",
            llm.model_name,
            self.DEFAULT_TEMPERATURE,
        )
        return llm

    def _build_structured_llm(self) -> Runnable:
        """Build structured output LLM from base LLM.

        Returns:
            Runnable with structured output configuration.
        """
        logger.debug(
            "Building structured LLM with output schema: %s", self.output.__name__
        )

        structured_llm = self.llm.with_structured_output(self.output)
        logger.debug("Structured LLM configured successfully")
        return structured_llm

    def _validate_api_key(self) -> None:
        """Validate that OPENAI_API_KEY is available.

        Raises:
            ApiKeyMissingError: If OPENAI_API_KEY is not found.
        """
        logger.debug("Validating OPENAI_API_KEY")

        api_key = self._get_env("OPENAI_API_KEY")
        if not api_key:
            error_msg = "Missing OPENAI_API_KEY. Set it in your .env file."
            logger.error(error_msg)
            raise ApiKeyMissingError(error_msg)

        logger.debug("OPENAI_API_KEY found")

    # --- Static methods ---
    @staticmethod
    def _build_messages(
        diff: str, system_prompt: str = SYSTEM_PROMPT
    ) -> List[BaseMessage]:
        """Build message list for LLM from diff and system prompt.

        Args:
            diff: Git diff content.
            system_prompt: System prompt for the LLM.

        Returns:
            List of BaseMessage instances for LLM input.
        """
        logger.debug("Building messages for diff (length: %d chars)", len(diff))

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"Please create a commit for this Git diff my dude:\n{diff}"
            ),
        ]

        logger.debug("Created %d messages", len(messages))
        return messages

    # --- Dunder methods ---
    def __repr__(self) -> str:
        """Return a machine-readable representation of ChatCommitDude."""
        return (
            f"{self.__class__.__name__}(model={self.model!r}, "
            f"max_tokens={self.max_tokens}, "
            f"output={self.output.__name__})"
        )

    def __str__(self) -> str:
        """Return a human-readable description of ChatCommitDude."""
        return f"ChatCommitDude using {self.model} with {self.max_tokens} max tokens"
