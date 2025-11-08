from typing import Any, Iterable, List

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from commit_dude import llm
from commit_dude.schemas import CommitMessageResponse


class FakeChatOpenAI:
    """Test double for ChatOpenAI using GenericFakeChatModel for responses."""

    def __init__(self, *, responses: Iterable[Any], num_tokens: int):
        self._responses = responses
        self._num_tokens = num_tokens
        self.invocations: List[List[Any]] = []
        self.last_diff: str | None = None

    def with_structured_output(self, schema: type[BaseModel]):
        fake_model = GenericFakeChatModel(messages=iter(self._responses))
        parent = self

        class StructuredModel:
            def invoke(self, messages):
                parent.invocations.append(messages)
                raw = fake_model.invoke(messages)
                if isinstance(raw, schema):
                    return raw
                if isinstance(raw, dict):
                    return schema(**raw)
                if isinstance(raw, AIMessage):
                    content = raw.content
                    if isinstance(content, str):
                        return schema.model_validate_json(content)
                    raise TypeError(f"Unsupported AIMessage content: {content!r}")
                if isinstance(raw, BaseModel):
                    return raw
                if isinstance(raw, str):
                    return schema.model_validate_json(raw)
                raise TypeError(f"Unsupported response type: {type(raw)!r}")

        return StructuredModel()

    def get_num_tokens(self, diff: str) -> int:
        self.last_diff = diff
        return self._num_tokens


def test_build_messages_produces_system_and_human_prompt():
    diff = "diff --git a/file b/file"

    messages = llm._build_messages(diff)

    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert diff in messages[1].content
    assert llm.SYSTEM_PROMPT in messages[0].content


def test_generate_commit_message_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="Missing OPENAI_API_KEY"):
        llm.generate_commit_message("diff")


def test_generate_commit_message_rejects_diffs_exceeding_token_limit(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    def fake_chat_factory(*args, **kwargs):
        return FakeChatOpenAI(responses=[], num_tokens=llm.MAX_TOKENS + 1)

    monkeypatch.setattr(llm, "ChatOpenAI", fake_chat_factory)

    with pytest.raises(ValueError, match="Diff is too long"):
        llm.generate_commit_message("large diff")


def test_generate_commit_message_returns_structured_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    responses = [
        AIMessage(
            content='{"agent_response": "Here you go!", "commit_message": "feat: add awesome change"}',
        )
    ]
    captured = {}

    def fake_chat_factory(*args, **kwargs):
        instance = FakeChatOpenAI(responses=responses, num_tokens=42)
        captured["instance"] = instance
        return instance

    monkeypatch.setattr(llm, "ChatOpenAI", fake_chat_factory)

    diff = "diff --git a/foo b/foo"
    result = llm.generate_commit_message(diff)

    assert isinstance(result, CommitMessageResponse)
    assert result.commit_message == "feat: add awesome change"
    assert result.agent_response == "Here you go!"
    assert captured["instance"].last_diff == diff
    assert captured["instance"].invocations
    assert diff in captured["instance"].invocations[0][1].content
