from pathlib import Path

from commit_dude.core.yaml_loader import YAMLLoader


class TestYAMLLoaderCompilePatterns:
    def test_compile_patterns_returns_compiled_regex_with_ids(self):
        loader = YAMLLoader()
        entries = [
            {
                "pattern": {
                    "name": "Example",
                    "regex": r"abc.+",
                    "confidence": "medium",
                }
            }
        ]

        compiled = loader.compile_patterns(entries, threshold=0.2)

        assert len(compiled) == 1
        assert compiled[0][0] == "Example"
        assert compiled[0][1].pattern == r"abc.+"

    def test_compile_patterns_skips_entries_below_threshold_or_missing_regex(self):
        loader = YAMLLoader()
        entries = [
            {
                "pattern": {
                    "name": "BelowThreshold",
                    "regex": r"should_not_compile",
                    "confidence": "low",
                }
            },
            {"pattern": {"name": "NoRegex"}},
        ]

        compiled = loader.compile_patterns(entries, threshold=0.5)

        assert compiled == []

    def test_compile_patterns_logs_warning_for_invalid_regex(self, caplog):
        loader = YAMLLoader()
        entries = [
            {
                "pattern": {
                    "name": "BadPattern",
                    "regex": r"[",
                    "confidence": "high",
                }
            }
        ]

        compiled = loader.compile_patterns(entries, threshold=0.5)

        assert compiled == []
        assert any("Bad regex for BadPattern" in message for message in caplog.messages)


class TestYAMLLoaderLoadPatterns:
    def test_load_patterns_returns_expected_entries(self):
        loader = YAMLLoader()

        patterns = loader.load_patterns(Path("tests/fixtures/test_patterns.yml"))

        assert len(patterns) == 2
        assert patterns[0]["pattern"]["name"] == "Stripe"
        assert patterns[1]["pattern"]["name"] == "Stripe API Key - 1"

    def test_load_patterns_allows_missing_signature(self, tmp_path):
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


class TestYAMLLoaderLoadAndCompile:
    def test_load_and_compile_returns_compiled_patterns(self):
        loader = YAMLLoader(patterns_yaml_path=Path("tests/fixtures/test_patterns.yml"))

        compiled = loader.load_and_compile(threshold=0.5)

        assert all(len(entry) == 2 for entry in compiled)
        assert compiled[0][0] == "Stripe"
        assert compiled[0][1].pattern == "[rs]k_live_[a-zA-Z0-9]{20,30}"

    def test_load_and_compile_applies_threshold(self):
        loader = YAMLLoader(patterns_yaml_path=Path("tests/fixtures/test_patterns.yml"))

        compiled = loader.load_and_compile(threshold=0.95)

        assert compiled == []
