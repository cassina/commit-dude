import re
import logging
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from commit_dude.core.middleware.pattern_detector_middleware import (
    SecretPatternDetectorMiddleware,
)
from commit_dude.core.yaml_loader import YAMLLoader
from commit_dude.core.config import REDACTION
from commit_dude.core.errors import SecretPatternDetectorError


# Ensure default loader is created and used when none is provided.
def test_init_loads_yaml_patterns_when_no_loader_provided():
    loader_instance = MagicMock()
    loader_instance.load_and_compile.return_value = ["compiled"]

    with patch(
        "commit_dude.core.middleware.pattern_detector_middleware.YAMLLoader",
        return_value=loader_instance,
    ) as loader_cls:
        middleware = SecretPatternDetectorMiddleware()

    loader_cls.assert_called_once_with()
    loader_instance.load_and_compile.assert_called_once_with(0.5)
    assert middleware.yaml_loader is loader_instance
    assert middleware.compiled == ["compiled"]


# Ensure injected YAMLLoader instance is used without creating a new one.
def test_init_uses_provided_yaml_loader_instance():
    provided_loader = MagicMock(spec=YAMLLoader)
    provided_loader.load_and_compile.return_value = ["provided"]

    with patch(
        "commit_dude.core.middleware.pattern_detector_middleware.YAMLLoader"
    ) as loader_cls:
        middleware = SecretPatternDetectorMiddleware(yaml_loader=provided_loader)

    loader_cls.assert_not_called()
    provided_loader.load_and_compile.assert_called_once_with(0.5)
    assert middleware.yaml_loader is provided_loader
    assert middleware.compiled == ["provided"]


# Ensure confidence threshold is forwarded to loader compilation.
def test_init_stores_confidence_threshold_correctly():
    provided_loader = MagicMock(spec=YAMLLoader)
    provided_loader.load_and_compile.return_value = []
    threshold = 0.75

    SecretPatternDetectorMiddleware(
        yaml_loader=provided_loader,
        confidence_threshold=threshold,
    )

    provided_loader.load_and_compile.assert_called_once_with(threshold)


# Ensure strategy value is stored exactly as provided.
def test_init_sets_strategy():
    provided_loader = MagicMock(spec=YAMLLoader)
    provided_loader.load_and_compile.return_value = []

    middleware = SecretPatternDetectorMiddleware(
        yaml_loader=provided_loader,
        strategy="redact",
    )

    assert middleware.strategy == "redact"


# Ensure default logger is created when none is provided.
def test_init_uses_default_logger_when_not_provided():
    default_logger = MagicMock()
    loader_instance = MagicMock()
    loader_instance.load_and_compile.return_value = []

    with patch(
        "commit_dude.core.middleware.pattern_detector_middleware.commit_dude_logger",
        return_value=default_logger,
    ) as logger_factory, patch(
        "commit_dude.core.middleware.pattern_detector_middleware.YAMLLoader",
        return_value=loader_instance,
    ):
        middleware = SecretPatternDetectorMiddleware()

    logger_factory.assert_called_once_with(
        "commit_dude.core.middleware.pattern_detector_middleware"
    )
    assert middleware._logger is default_logger


# Detects single pattern match.
def test_detect_returns_single_match():
    compiled = [("pattern_1", re.compile(r"secret"))]
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = compiled
    middleware = SecretPatternDetectorMiddleware(yaml_loader=loader)

    result = middleware._detect("contains secret value")

    assert result == [("pattern_1", "secret")]


# Detects multiple pattern matches in the same text.
def test_detect_returns_multiple_matches():
    compiled = [("pattern_multi", re.compile(r"token"))]
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = compiled
    middleware = SecretPatternDetectorMiddleware(yaml_loader=loader)

    result = middleware._detect("first token and second token")

    assert result == [("pattern_multi", "token"), ("pattern_multi", "token")]


# Returns empty list when no patterns match.
def test_detect_returns_empty_list_when_no_match():
    compiled = [("pattern_none", re.compile(r"nomatch"))]
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = compiled
    middleware = SecretPatternDetectorMiddleware(yaml_loader=loader)

    result = middleware._detect("safe content")

    assert result == []


# Supports overlapping regex patterns.
def test_detect_handles_overlapping_patterns():
    compiled = [
        ("pattern_full", re.compile(r"sk_test_[0-9]+")),
        ("pattern_partial", re.compile(r"test_[0-9]+")),
    ]
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = compiled
    middleware = SecretPatternDetectorMiddleware(yaml_loader=loader)

    result = middleware._detect("sk_test_12345")

    assert result == [
        ("pattern_full", "sk_test_12345"),
        ("pattern_partial", "test_12345"),
    ]


# Ignores empty or None text inputs.
@pytest.mark.parametrize("text", [None, ""])
def test_detect_returns_empty_for_empty_or_none(text):
    compiled = [("pattern_any", re.compile(r".+"))]
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = compiled
    middleware = SecretPatternDetectorMiddleware(yaml_loader=loader)

    result = middleware._detect(text)

    assert result == []

def test_before_model_no_patterns_returns_none():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    logger = MagicMock()
    middleware = SecretPatternDetectorMiddleware(
        yaml_loader=loader, logger=logger, strategy="block"
    )
    middleware._detect = MagicMock(return_value=[])

    state = {"messages": [HumanMessage(content="hello world")]}

    result = middleware.before_model(state, runtime=MagicMock())

    assert result is None


def test_before_model_no_patterns_does_not_modify_messages():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(yaml_loader=loader, strategy="block")
    middleware._detect = MagicMock(return_value=[])

    message = HumanMessage(content="keep me")
    state = {"messages": [message]}

    middleware.before_model(state, runtime=MagicMock())

    assert state["messages"][0] is message
    assert state["messages"][0].content == "keep me"


def test_before_model_logs_no_pattern_detected(caplog):
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    logger = logging.getLogger("pattern-detector-no-matches")
    logger.setLevel(logging.DEBUG)
    logger.propagate = True
    middleware = SecretPatternDetectorMiddleware(
        yaml_loader=loader, logger=logger, strategy="block"
    )
    middleware._detect = MagicMock(return_value=[])

    state = {"messages": [HumanMessage(content="no secrets here")]}

    with caplog.at_level(logging.DEBUG):
        middleware.before_model(state, runtime=MagicMock())

    assert "No secret patterns detected." in caplog.text


def test_before_model_block_mode_raises_on_match():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(yaml_loader=loader, strategy="block")
    middleware._detect = MagicMock(return_value=[("PID-1", "secret")])

    state = {"messages": [HumanMessage(content="secret value")]}

    with pytest.raises(SecretPatternDetectorError):
        middleware.before_model(state, runtime=MagicMock())


def test_before_model_block_mode_error_contains_pid():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(yaml_loader=loader, strategy="block")
    middleware._detect = MagicMock(return_value=[("PID-123", "secret-token")])

    state = {"messages": [HumanMessage(content="secret-token")]}

    with pytest.raises(SecretPatternDetectorError) as excinfo:
        middleware.before_model(state, runtime=MagicMock())

    assert "PID-123" in str(excinfo.value)


def test_before_model_block_mode_does_not_modify_messages_on_error():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(yaml_loader=loader, strategy="block")
    middleware._detect = MagicMock(return_value=[("PID-1", "secret")])

    original_message = HumanMessage(content="secret")
    state = {"messages": [original_message]}

    with pytest.raises(SecretPatternDetectorError):
        middleware.before_model(state, runtime=MagicMock())

    assert state["messages"][0] is original_message
    assert state["messages"][0].content == "secret"


def test_before_model_block_mode_stops_before_redaction():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    logger = MagicMock()
    middleware = SecretPatternDetectorMiddleware(
        yaml_loader=loader, logger=logger, strategy="block"
    )
    middleware._detect = MagicMock(return_value=[("PID-1", "secret")])

    with pytest.raises(SecretPatternDetectorError):
        middleware.before_model(
            {"messages": [HumanMessage(content="secret")]}, runtime=MagicMock()
        )

    warning_messages = [call.args[0] for call in logger.warning.call_args_list]
    assert any("Strategy: block" in msg for msg in warning_messages)
    assert not any("Redacting" in msg for msg in warning_messages)


def test_before_model_redact_mode_replaces_detected_text():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(
        yaml_loader=loader, strategy="redact"
    )
    middleware._detect = MagicMock(return_value=[("PID-1", "secret")])

    state = {"messages": [HumanMessage(content="my secret text")]}

    result = middleware.before_model(state, runtime=MagicMock())

    sanitized = result["messages"][0].content
    assert REDACTION in sanitized
    assert "secret" not in sanitized


def test_before_model_redact_mode_returns_new_state():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(
        yaml_loader=loader, strategy="redact"
    )
    middleware._detect = MagicMock(return_value=[("PID-1", "secret")])

    original_message = HumanMessage(content="secret")
    state = {"messages": [original_message]}

    result = middleware.before_model(state, runtime=MagicMock())

    assert result is not None
    assert result["messages"][0] is not original_message
    assert state["messages"][0].content == "secret"


def test_before_model_redact_mode_redacts_multiple_matches():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(
        yaml_loader=loader, strategy="redact"
    )
    middleware._detect = MagicMock(return_value=[("PID-1", "alpha"), ("PID-2", "beta")])

    state = {"messages": [HumanMessage(content="alpha then beta")]}

    result = middleware.before_model(state, runtime=MagicMock())

    sanitized = result["messages"][0].content
    assert "alpha" not in sanitized
    assert "beta" not in sanitized
    assert sanitized.count(REDACTION) == 2


def test_before_model_redact_mode_redacts_repeated_pattern_occurrences():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(
        yaml_loader=loader, strategy="redact"
    )
    middleware._detect = MagicMock(return_value=[("PID-1", "secret"), ("PID-1", "secret")])

    state = {"messages": [HumanMessage(content="secret secret")]}

    result = middleware.before_model(state, runtime=MagicMock())

    sanitized = result["messages"][0].content
    assert sanitized.count(REDACTION) == 2
    assert "secret" not in sanitized


def test_before_model_redact_mode_preserves_non_string_messages():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(
        yaml_loader=loader, strategy="redact"
    )
    middleware._detect = MagicMock(return_value=[("PID-1", "secret")])

    ai_message = AIMessage(content=[{"text": "structured"}])
    state = {"messages": [ai_message]}

    result = middleware.before_model(state, runtime=MagicMock())

    assert result["messages"][0] is ai_message
    assert result["messages"][0].content == [{"text": "structured"}]


def test_before_model_redact_mode_logs_replacement_details():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    logger = MagicMock()
    middleware = SecretPatternDetectorMiddleware(
        yaml_loader=loader, logger=logger, strategy="redact"
    )
    middleware._detect = MagicMock(return_value=[("PID-1", "secret"), ("PID-2", "token")])

    middleware.before_model(
        {"messages": [HumanMessage(content="secret token")]}, runtime=MagicMock()
    )

    warning_messages = [call.args[0] for call in logger.warning.call_args_list]
    assert any("Redacting secret patterns detected" in msg for msg in warning_messages)
    assert any("Replaced 2 patterns" in msg for msg in warning_messages)


def test_before_model_redact_mode_handles_missing_or_none_content():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(
        yaml_loader=loader, strategy="redact"
    )
    middleware._detect = MagicMock(return_value=[("PID-1", "secret")])

    class DummyMessage:
        def __init__(self):
            self.content = None

    state = {"messages": [DummyMessage()]}

    result = middleware.before_model(state, runtime=MagicMock())

    assert result["messages"][0].content is None


def test_before_model_concatenates_multiple_message_contents():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(
        yaml_loader=loader, strategy="block"
    )
    spy = MagicMock(return_value=[])
    middleware._detect = spy

    messages = [
        HumanMessage(content="first"),
        HumanMessage(content="second"),
    ]

    middleware.before_model({"messages": messages}, runtime=MagicMock())

    spy.assert_called_once_with("first second")


def test_before_model_ignores_non_string_message_contents():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(
        yaml_loader=loader, strategy="block"
    )
    spy = MagicMock(return_value=[])
    middleware._detect = spy

    ai_message = AIMessage(content=[{"text": "structured"}])
    messages = [HumanMessage(content="plain"), ai_message]

    middleware.before_model({"messages": messages}, runtime=MagicMock())

    spy.assert_called_once_with("plain")


def test_before_model_redact_mode_uses_model_copy_for_base_message():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(
        yaml_loader=loader, strategy="redact"
    )
    middleware._detect = MagicMock(return_value=[("PID-1", "secret")])

    message = MagicMock(spec=BaseMessage)
    message.content = "secret data"
    replacement = MagicMock()
    message.model_copy.return_value = replacement

    result = middleware.before_model({"messages": [message]}, runtime=MagicMock())

    message.model_copy.assert_called_once_with(update={"content": REDACTION + " data"})
    assert result["messages"][0] is replacement


def test_before_model_logs_performance_start_and_end(caplog):
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    logger = logging.getLogger("perf-logger")
    logger.setLevel(logging.DEBUG)
    logger.propagate = True
    middleware = SecretPatternDetectorMiddleware(
        yaml_loader=loader, logger=logger, strategy="block"
    )
    middleware._detect = MagicMock(return_value=[])

    with caplog.at_level(logging.DEBUG):
        middleware.before_model(
            {"messages": [HumanMessage(content="no secrets")]}, runtime=MagicMock()
        )

    assert "Checking for secret patterns" in caplog.text
    assert "Finished secret pattern detection in" in caplog.text


def test_before_model_redact_mode_logs_replaced_count(caplog):
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(
        yaml_loader=loader, strategy="redact"
    )
    middleware._detect = MagicMock(return_value=[("PID-1", "secret")])

    with caplog.at_level(logging.WARNING):
        middleware.before_model(
            {"messages": [HumanMessage(content="secret info")]}, runtime=MagicMock()
        )

    assert "Replaced 1 patterns" in caplog.text


def test_detect_returns_empty_when_compiled_patterns_empty():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(yaml_loader=loader)

    assert middleware._detect("some text") == []


def test_before_model_handles_empty_message_list():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(yaml_loader=loader, strategy="block")
    middleware._detect = MagicMock(return_value=[])

    result = middleware.before_model({"messages": []}, runtime=MagicMock())

    assert result is None


def test_before_model_handles_message_without_content_attribute():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(yaml_loader=loader, strategy="block")
    middleware._detect = MagicMock(return_value=[])

    class MessageWithoutContent:
        def __init__(self):
            self.extra = "data"

    result = middleware.before_model(
        {"messages": [MessageWithoutContent()]}, runtime=MagicMock()
    )

    middleware._detect.assert_called_once_with("")
    assert result is None


def test_before_model_handles_mixed_message_types():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(yaml_loader=loader, strategy="block")
    spy = MagicMock(return_value=[])
    middleware._detect = spy

    messages = [
        HumanMessage(content="human text"),
        AIMessage(content=[{"text": "structured"}]),
        SystemMessage(content="system directive"),
    ]

    middleware.before_model({"messages": messages}, runtime=MagicMock())

    spy.assert_called_once_with("human text system directive")


def test_before_model_accepts_unused_runtime_argument():
    loader = MagicMock(spec=YAMLLoader)
    loader.load_and_compile.return_value = []
    middleware = SecretPatternDetectorMiddleware(yaml_loader=loader, strategy="block")
    middleware._detect = MagicMock(return_value=[])
    runtime = MagicMock()

    result = middleware.before_model(
        {"messages": [HumanMessage(content="irrelevant")]}, runtime=runtime
    )

    assert result is None
