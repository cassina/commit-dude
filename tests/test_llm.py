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
        self.invocations: list[Any] = []
        self.configs: list[Any] = []

    def invoke(
        self,
        input: Any,
        config=None,
        **kwargs
    ) -> CommitMessageResponse:
        """Return predefined response while tracking inputs."""

        self.invocations.append(input)
        self.configs.append(config)
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
        self.last_get_num_tokens_input: Optional[str] = None

    def with_structured_output(self, output: Any) -> "FakeStructuredLLM":
        """Track structured output calls and return fake runnable."""

        self.with_structured_output_called = True
        self.output_model = output
        return FakeStructuredLLM(self._structured_response)

    def get_num_tokens(self, _: str) -> int:
        """Return predetermined token count for diff inspection."""

        self.last_get_num_tokens_input = _
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

def _build_stubbed_chat_commit_dude(
    monkeypatch: pytest.MonkeyPatch,
    *,
    validate_api_key: bool = False,
    get_env=mock_get_env_with_key,
    llm: Optional[FakeCommitDudeChat] = None,
    structured_llm: Optional[FakeStructuredLLM] = None,
) -> ChatCommitDude:
    """Helper to create ChatCommitDude with fakes without touching network."""

    dummy_llm = llm or FakeCommitDudeChat()
    monkeypatch.setattr(ChatCommitDude, "_build_model", lambda self: dummy_llm)

    if structured_llm is None:
        monkeypatch.setattr(
            ChatCommitDude,
            "_build_structured_llm",
            lambda self: FakeStructuredLLM(
                CommitMessageResponse(agent_response="", commit_message="")
            ),
        )
    else:
        monkeypatch.setattr(
            ChatCommitDude,
            "_build_structured_llm",
            lambda self: structured_llm,
        )

    return ChatCommitDude(
        validate_api_key=validate_api_key,
        get_env=get_env,
    )


def test_validate_api_key_present_does_not_raise(monkeypatch):
    """_validate_api_key succeeds when the key exists."""

    chat_dude = _build_stubbed_chat_commit_dude(monkeypatch, validate_api_key=False)

    # Should not raise when API key is provided
    chat_dude._validate_api_key()


def test_validate_api_key_missing_raises_error(monkeypatch):
    """_validate_api_key raises ApiKeyMissingError when key is missing."""

    chat_dude = _build_stubbed_chat_commit_dude(
        monkeypatch,
        validate_api_key=False,
        get_env=mock_get_env_without_key,
    )

    with pytest.raises(ApiKeyMissingError):
        chat_dude._validate_api_key()


def test_build_messages_creates_system_and_human_messages():
    """_build_messages constructs the expected LangChain message sequence."""

    diff = "diff --git a/foo b/foo"
    messages = ChatCommitDude._build_messages(diff)

    assert len(messages) == 2
    assert messages[0].__class__.__name__ == "SystemMessage"
    assert messages[1].__class__.__name__ == "HumanMessage"
    assert diff in messages[1].content


def test_build_messages_uses_custom_system_prompt():
    """_build_messages should respect an override for the system prompt."""

    diff = "diff --git a/foo b/foo"
    custom_prompt = "custom system prompt"

    messages = ChatCommitDude._build_messages(diff, system_prompt=custom_prompt)

    assert messages[0].content == custom_prompt


def test_repr_contains_class_and_model(monkeypatch):
    """__repr__ includes the class name and selected model."""

    chat_dude = _build_stubbed_chat_commit_dude(monkeypatch)

    repr_str = repr(chat_dude)
    assert chat_dude.__class__.__name__ in repr_str
    assert chat_dude.model in repr_str


def test_str_contains_model_name(monkeypatch):
    """__str__ provides a human readable message with the model name."""

    chat_dude = _build_stubbed_chat_commit_dude(monkeypatch)

    human_str = str(chat_dude)
    assert chat_dude.model in human_str


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


def test_end_to_end_invoke_with_mocks(monkeypatch):
    """invoke should run through validation and message generation using fakes."""

    fake_response = CommitMessageResponse(
        agent_response="sure thing",
        commit_message="feat: add new feature",
    )
    fake_llm = FakeCommitDudeChat(token_count=12, structured_response=fake_response)

    chat_dude = ChatCommitDude(
        llm=fake_llm,
        validate_api_key=False,
    )

    diff = "diff --git a/foo b/foo\n+"
    result = chat_dude.invoke(diff)

    assert result.model_dump() == fake_response.model_dump()
    assert fake_llm.with_structured_output_called is True
    assert fake_llm.output_model is CommitMessageResponse
    assert fake_llm.last_get_num_tokens_input == diff

    assert len(chat_dude.structured_llm.invocations) == 1
    messages = chat_dude.structured_llm.invocations[0]
    assert messages[0].__class__.__name__ == "SystemMessage"
    assert messages[1].__class__.__name__ == "HumanMessage"
    assert "Please create a commit" in messages[1].content


def test_invoke_with_empty_diff_still_calls_methods():
    """Even an empty diff should trigger validation and generation flows."""

    fake_response = CommitMessageResponse(agent_response="ok", commit_message="msg")
    fake_llm = FakeCommitDudeChat(structured_response=fake_response)
    chat_dude = ChatCommitDude(
        llm=fake_llm,
        validate_api_key=False,
    )

    calls = []

    def fake_validate(diff: str) -> int:
        calls.append(("validate", diff))
        return 0

    def fake_generate(diff: str) -> CommitMessageResponse:
        calls.append(("generate", diff))
        return fake_response

    chat_dude._validate_num_tokens = fake_validate
    chat_dude._generate_commit_message = fake_generate

    result = chat_dude.invoke("")

    assert result.model_dump() == fake_response.model_dump()
    assert calls == [("validate", ""), ("generate", "")]

