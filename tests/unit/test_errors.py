def test_custom_exceptions_inheritance():
    """Test that custom exceptions inherit from base exception."""
    from commit_dude.errors import (
        ChatCommitDudeError,
        TokenLimitExceededError,
        ApiKeyMissingError,
    )

    assert issubclass(TokenLimitExceededError, ChatCommitDudeError)
    assert issubclass(ApiKeyMissingError, ChatCommitDudeError)
    assert issubclass(ChatCommitDudeError, Exception)
