#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for ChatCommitDude class."""

from typing import Iterable, List, Any, Optional

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable

from commit_dude.llm import ChatCommitDude
from commit_dude.schemas import CommitMessageResponse
from commit_dude.errors import TokenLimitExceededError, ApiKeyMissingError


class FakeCommitDudeChat(GenericFakeChatModel):
    """Fake chat model for testing ChatCommitDude functionality."""
    
    def __init__(self, responses: List[str], token_count: int = 50) -> None:
        """Initialize fake chat model with predefined responses.
        
        Args:
            responses: List of response strings to cycle through.
            token_count: Fixed token count to return for any input.
        """
        def message_generator() -> Iterable[AIMessage]:
            for response in responses:
                yield AIMessage(content=response)
        
        super().__init__(messages=message_generator())
        object.__setattr__(self, 'token_count', token_count)
    
    def get_num_tokens(self, text: str) -> int:
        """Return fixed token count for testing.
        
        Args:
            text: Input text (ignored).
            
        Returns:
            Fixed token count set during initialization.
        """
        return self.token_count


class FakeStructuredLLM(Runnable):
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

def test_init_with_valid_api_key():
    """Test successful initialization with valid API key."""
    chat_dude = ChatCommitDude(get_env=mock_get_env_with_key)
    assert chat_dude.model == "gpt-4o-mini"

def test_repr_and_str_methods():
    """Test __repr__ and __str__ methods return expected formats."""
    chat_dude = ChatCommitDude(validate_api_key=False)
    
    repr_str = repr(chat_dude)
    assert "ChatCommitDude" in repr_str
    assert "gpt-4o-mini" in repr_str
    
    str_str = str(chat_dude)
    assert "ChatCommitDude using gpt-4o-mini" in str_str

