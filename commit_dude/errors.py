class ChatCommitDudeError(Exception):
    """Base exception for ChatCommitDude errors."""


class TokenLimitExceededError(ChatCommitDudeError):
    """Raised when diff exceeds maximum token limit."""


class ApiKeyMissingError(ChatCommitDudeError):
    """Raised when OPENAI_API_KEY is not found."""


class SecretPatternDetectorError(ChatCommitDudeError):
    """Raised when the secret pattern detector fails."""
