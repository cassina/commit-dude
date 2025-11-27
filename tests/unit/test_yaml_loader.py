from pathlib import Path


from commit_dude.core.yaml_loader import YAMLLoader


def test_load_patterns_returns_expected_entries():
    loader = YAMLLoader()

    patterns = loader.load_patterns(Path("tests/fixtures/test_patterns.yml"))

    assert len(patterns) == 2
    assert patterns[0]["pattern"]["name"] == "Stripe"
    assert patterns[1]["pattern"]["name"] == "Stripe API Key - 1"


def test_load_patterns_allows_missing_signature(tmp_path):
    patterns_file = tmp_path / "patterns.yml"
    patterns_file.write_text(
        """
        version: 0.0.2
        patterns:
          - pattern:
              name: Example Pattern
              regex: example
              confidence: medium
        """,
        encoding="utf-8",
    )

    loader = YAMLLoader()

    patterns = loader.load_patterns(patterns_file)

    assert len(patterns) == 1
    assert patterns[0]["pattern"]["name"] == "Example Pattern"
