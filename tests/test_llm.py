#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for ChatCommitDude class."""

import logging
import sys
from pathlib import Path
from typing import Any, Optional

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from commit_dude.llm import ChatCommitDude
from commit_dude.schemas import CommitMessageResponse
from commit_dude.errors import TokenLimitExceededError, ApiKeyMissingError


class FakeStructuredLLM:
    """Fake structured LLM for testing commit message generation."""

    def __init__(self, response: CommitMessageResponse) -> None:
        """Initialize with predefined response.

        Args:
            response: CommitMessageResponse to return on invoke.
        """
        self.response = response

    def invoke(
        self,
        input: Any,
        config=None,
        **kwargs
    ) -> CommitMessageResponse:
        """Return predefined response.

        Args:
            input: Input data (ignored).
            config: Configuration (ignored).
            **kwargs: Additional arguments (ignored).

        Returns:
            Predefined CommitMessageResponse.
        """
        return self.response


class FakeCommitDudeChat:
    """Minimal chat model stub for exercising ChatCommitDude logic in tests."""

    def __init__(
        self,
        *,
        token_count: int = 10,
        structured_response: Optional[CommitMessageResponse] = None,
    ) -> None:
        """Initialize fake chat model with optional structured response."""

        self.token_count = token_count
        self.with_structured_output_called = False
        self.output_model: Optional[Any] = None
        self._structured_response = structured_response or CommitMessageResponse(
            agent_response="",
            commit_message="",
        )

    def with_structured_output(self, output: Any) -> "FakeStructuredLLM":
        """Track structured output calls and return fake runnable."""

        self.with_structured_output_called = True
        self.output_model = output
        return FakeStructuredLLM(self._structured_response)

    def get_num_tokens(self, _: str) -> int:
        """Return predetermined token count for diff inspection."""

        return self.token_count


def mock_get_env_with_key(key: str) -> Optional[str]:
    """Mock environment getter that returns API key.
    
    Args:
        key: Environment variable name.
        
    Returns:
        API key if requested, None otherwise.
    """
    return "sk-test-key" if key == "OPENAI_API_KEY" else None


def mock_get_env_without_key(key: str) -> Optional[str]:
    """Mock environment getter that returns None for all keys.

    Args:
        key: Environment variable name (ignored).

    Returns:
        Always None.
    """
    return None


def test_init_with_valid_api_key(monkeypatch):
    """Test successful initialization with valid API key."""

    dummy_llm = FakeCommitDudeChat()

    monkeypatch.setattr(ChatCommitDude, "_build_model", lambda self: dummy_llm)
    monkeypatch.setattr(
        ChatCommitDude,
        "_build_structured_llm",
        lambda self: "structured-llm",
    )

    chat_dude = ChatCommitDude(get_env=mock_get_env_with_key)
    assert chat_dude.model == "gpt-4o-mini"

def test_repr_and_str_methods(monkeypatch):
    """Test __repr__ and __str__ methods return expected formats."""

    dummy_llm = FakeCommitDudeChat()

    monkeypatch.setattr(ChatCommitDude, "_build_model", lambda self: dummy_llm)
    monkeypatch.setattr(
        ChatCommitDude,
        "_build_structured_llm",
        lambda self: "structured-llm",
    )

    chat_dude = ChatCommitDude(validate_api_key=False)

    repr_str = repr(chat_dude)
    assert "ChatCommitDude" in repr_str
    assert "gpt-4o-mini" in repr_str

    str_str = str(chat_dude)
    assert "ChatCommitDude using gpt-4o-mini" in str_str


def test_init_without_api_key_raises_error(monkeypatch):
    """Ensure initialization fails when API key validation is enabled."""

    # Avoid building real models if validation unexpectedly passes
    monkeypatch.setattr(ChatCommitDude, "_build_model", lambda self: FakeCommitDudeChat())
    monkeypatch.setattr(
        ChatCommitDude,
        "_build_structured_llm",
        lambda self: FakeStructuredLLM(
            CommitMessageResponse(agent_response="", commit_message="")
        ),
    )

    with pytest.raises(ApiKeyMissingError):
        ChatCommitDude(get_env=mock_get_env_without_key)


def test_init_skips_api_key_validation_when_disabled(monkeypatch):
    """Validation can be skipped allowing initialization without API key."""

    dummy_llm = FakeCommitDudeChat()
    structured_called = False

    def fake_build_model(self):
        return dummy_llm

    def fake_build_structured(self):
        nonlocal structured_called
        structured_called = True
        return "structured-llm"

    monkeypatch.setattr(ChatCommitDude, "_build_model", fake_build_model)
    monkeypatch.setattr(ChatCommitDude, "_build_structured_llm", fake_build_structured)

    chat_dude = ChatCommitDude(
        validate_api_key=False,
        get_env=mock_get_env_without_key,
    )

    assert chat_dude.llm is dummy_llm
    assert structured_called is True


def test_init_uses_default_model_and_output(monkeypatch):
    """Defaults are applied when not provided explicitly."""

    dummy_llm = FakeCommitDudeChat()

    monkeypatch.setattr(ChatCommitDude, "_build_model", lambda self: dummy_llm)
    monkeypatch.setattr(
        ChatCommitDude,
        "_build_structured_llm",
        lambda self: "structured-llm",
    )

    chat_dude = ChatCommitDude(get_env=mock_get_env_with_key)

    assert chat_dude.model == ChatCommitDude.DEFAULT_MODEL
    assert chat_dude.output is CommitMessageResponse
    assert chat_dude.llm is dummy_llm


def test_init_with_injected_llm_and_structured_llm(monkeypatch):
    """Injected dependencies should be preserved and builders not invoked."""

    def fail_build_model(self):  # pragma: no cover - defensive check
        raise AssertionError("_build_model should not run")

    def fail_build_structured(self):  # pragma: no cover - defensive check
        raise AssertionError("_build_structured_llm should not run")

    monkeypatch.setattr(ChatCommitDude, "_build_model", fail_build_model)
    monkeypatch.setattr(ChatCommitDude, "_build_structured_llm", fail_build_structured)

    injected_llm = FakeCommitDudeChat()
    injected_structured = FakeStructuredLLM(
        CommitMessageResponse(agent_response="hi", commit_message="msg")
    )

    chat_dude = ChatCommitDude(
        llm=injected_llm,
        structured_llm=injected_structured,
        validate_api_key=False,
    )

    assert chat_dude.llm is injected_llm
    assert chat_dude.structured_llm is injected_structured


def test_build_model_called_when_no_llm_provided(monkeypatch):
    """LLM builder should run when no LLM dependency supplied."""

    dummy_llm = FakeCommitDudeChat()
    build_model_called = False

    def fake_build_model(self):
        nonlocal build_model_called
        build_model_called = True
        return dummy_llm

    monkeypatch.setattr(ChatCommitDude, "_build_model", fake_build_model)
    monkeypatch.setattr(
        ChatCommitDude,
        "_build_structured_llm",
        lambda self: "structured-llm",
    )

    chat_dude = ChatCommitDude(get_env=mock_get_env_with_key)

    assert build_model_called is True
    assert chat_dude.llm is dummy_llm


def test_build_structured_llm_called_when_no_structured_llm_provided(monkeypatch):
    """Structured LLM builder should run when not provided."""

    dummy_llm = FakeCommitDudeChat()
    structured_called = False

    monkeypatch.setattr(ChatCommitDude, "_build_model", lambda self: dummy_llm)

    def fake_build_structured(self):
        nonlocal structured_called
        structured_called = True
        return "structured-llm"

    monkeypatch.setattr(ChatCommitDude, "_build_structured_llm", fake_build_structured)

    chat_dude = ChatCommitDude(get_env=mock_get_env_with_key)

    assert structured_called is True
    assert chat_dude.structured_llm == "structured-llm"


def test_validate_num_tokens_within_limit():
    """Token validation returns count when within limit."""

    llm = FakeCommitDudeChat(token_count=50)
    response = CommitMessageResponse(agent_response="ok", commit_message="msg")
    chat_dude = ChatCommitDude(
        llm=llm,
        structured_llm=FakeStructuredLLM(response),
        max_tokens=100,
        validate_api_key=False,
    )

    tokens = chat_dude._validate_num_tokens("diff")

    assert tokens == 50


def test_validate_num_tokens_exceeds_limit():
    """Token validation raises error when diff is too long."""

    llm = FakeCommitDudeChat(token_count=150)
    response = CommitMessageResponse(agent_response="ok", commit_message="msg")
    chat_dude = ChatCommitDude(
        llm=llm,
        structured_llm=FakeStructuredLLM(response),
        max_tokens=100,
        validate_api_key=False,
    )

    with pytest.raises(TokenLimitExceededError):
        chat_dude._validate_num_tokens("diff")


def test_validate_num_tokens_logs_information(caplog):
    """Validation should log informational token usage details."""

    caplog.set_level(logging.INFO, logger="commit_dude.llm")

    llm = FakeCommitDudeChat(token_count=40)
    response = CommitMessageResponse(agent_response="ok", commit_message="msg")
    chat_dude = ChatCommitDude(
        llm=llm,
        structured_llm=FakeStructuredLLM(response),
        max_tokens=100,
        validate_api_key=False,
    )

    chat_dude._validate_num_tokens("diff content")

    assert any("Diff token count" in record.message for record in caplog.records)

