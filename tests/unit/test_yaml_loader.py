from pathlib import Path

import pytest
import yaml

from commit_dude.core.yaml_loader import SIGNATURE_OVERRIDE_ENV, YAMLLoader


def test_load_patterns_returns_expected_entries(monkeypatch):
    monkeypatch.setenv(SIGNATURE_OVERRIDE_ENV, "test-generated-hash")
    loader = YAMLLoader()

    patterns = loader.load_patterns(Path("tests/fixtures/test_patterns.yml"))

    assert len(patterns) == 2
    assert patterns[0]["pattern"]["name"] == "Stripe"
    assert patterns[1]["pattern"]["name"] == "Stripe API Key - 1"


def test_load_patterns_raises_for_invalid_signature(monkeypatch):
    monkeypatch.setenv(SIGNATURE_OVERRIDE_ENV, "unexpected-hash")
    loader = YAMLLoader()

    with pytest.raises(yaml.YAMLError):
        loader.load_patterns(Path("tests/fixtures/test_patterns.yml"))
