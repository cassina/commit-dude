from unittest.mock import Mock

import pytest

from commit_dude.core import agents
from commit_dude.core.errors import ApiKeyMissingError


def test_agent_init_loads_api_key(monkeypatch):
    # Arrange
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    mock_load_dotenv = Mock()
    mock_chat_openai = Mock()
    monkeypatch.setattr(agents, "load_dotenv", mock_load_dotenv)
    monkeypatch.setattr(agents, "ChatOpenAI", mock_chat_openai)

    # Act
    agents.CommitDudeAgent()

    # Assert
    mock_load_dotenv.assert_called_once()
    mock_chat_openai.assert_called_once_with(model="gpt-5-mini", temperature=0.5)


def test_agent_init_raises_when_api_key_missing(monkeypatch):
    # Arrange
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock_load_dotenv = Mock()
    mock_chat_openai = Mock()
    monkeypatch.setattr(agents, "load_dotenv", mock_load_dotenv)
    monkeypatch.setattr(agents, "ChatOpenAI", mock_chat_openai)

    # Act & Assert
    with pytest.raises(ApiKeyMissingError):
        agents.CommitDudeAgent()

    mock_load_dotenv.assert_called_once()
    mock_chat_openai.assert_not_called()
