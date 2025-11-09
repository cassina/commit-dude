from typing import Iterable, List, Any

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable

from commit_dude.llm import ChatCommitDude
from commit_dude.schemas import CommitMessageResponse


class FakeCommitDudeChat(GenericFakeChatModel):
    def __init__(self, responses: List[str], token_count: int = 50):
        def message_generator() -> Iterable[AIMessage]:
            for response in responses:
                yield AIMessage(content=response)
        
        super().__init__(messages=message_generator())
        object.__setattr__(self, 'token_count', token_count)
    
    def get_num_tokens(self, text: str) -> int:
        return self.token_count


class FakeStructuredLLM(Runnable):
    def __init__(self, response: CommitMessageResponse):
        self.response = response
    
    def invoke(self, input: Any, config=None, **kwargs) -> CommitMessageResponse:
        return self.response


def mock_get_env_with_key(key: str) -> str:
    return "sk-test-key" if key == "OPENAI_API_KEY" else None


def mock_get_env_without_key(key: str) -> str:
    return None


def test_build_messages_produces_system_and_human_prompt():
    diff = "some git diff content"
    messages = ChatCommitDude.build_messages(diff)
    
    assert len(messages) == 2
    assert "some git diff content" in messages[1].content


def test_generate_commit_message_requires_api_key():
    with pytest.raises(ValueError, match="Missing OPENAI_API_KEY"):
        ChatCommitDude(get_env=mock_get_env_without_key)


def test_generate_commit_message_rejects_diffs_exceeding_token_limit():
    fake_llm = FakeCommitDudeChat(["test response"], token_count=5000)
    fake_structured = FakeStructuredLLM(CommitMessageResponse(
        commit_message="feat(test): add fake implementation",
        agent_response="This is a test response"
    ))
    
    chat_dude = ChatCommitDude(
        llm=fake_llm,
        structured_llm=fake_structured,
        max_tokens=1000,
        validate_api_key=False
    )
    
    with pytest.raises(ValueError, match="Diff is too long"):
        chat_dude.validate_num_tokens("some long diff")


def test_generate_commit_message_returns_structured_response():
    fake_llm = FakeCommitDudeChat(["test response"], token_count=50)
    
    fake_structured = FakeStructuredLLM(CommitMessageResponse(
        commit_message="feat(test): add fake implementation",
        agent_response="This is a test response"
    ))
    
    chat_dude = ChatCommitDude(
        llm=fake_llm,
        structured_llm=fake_structured,
        validate_api_key=False
    )
    
    result = chat_dude.invoke("some diff")
    
    assert isinstance(result, CommitMessageResponse)
    assert result.commit_message == "feat(test): add fake implementation"
    assert result.agent_response == "This is a test response"


def test_init_with_valid_api_key():
    chat_dude = ChatCommitDude(get_env=mock_get_env_with_key)
    assert chat_dude.model == "gpt-4o-mini"


def test_validate_num_tokens_passes_when_under_limit():
    fake_llm = FakeCommitDudeChat(["test response"], token_count=50)
    fake_structured = FakeStructuredLLM(CommitMessageResponse(
        commit_message="feat(test): add fake implementation",
        agent_response="This is a test response"
    ))
    
    chat_dude = ChatCommitDude(
        llm=fake_llm,
        structured_llm=fake_structured,
        max_tokens=1000,
        validate_api_key=False
    )
    
    result = chat_dude.validate_num_tokens("short diff")
    assert result == 50
