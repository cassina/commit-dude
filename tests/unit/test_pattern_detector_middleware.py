from unittest.mock import MagicMock, patch

from commit_dude.core.middleware.pattern_detector_middleware import (
    SecretPatternDetectorMiddleware,
)
from commit_dude.core.yaml_loader import YAMLLoader


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
