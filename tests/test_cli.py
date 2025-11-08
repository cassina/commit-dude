"""Unit tests for :mod:`commit_dude.cli`."""

from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class _BaseModel:
    def __init__(self, **data):
        for key, value in data.items():
            setattr(self, key, value)


try:  # pragma: no cover - exercised implicitly via imports
    import pydantic  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - only in minimal envs
    sys.modules.setdefault("pydantic", SimpleNamespace(BaseModel=_BaseModel))


try:  # pragma: no cover
    import pyperclip  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    sys.modules.setdefault("pyperclip", SimpleNamespace(copy=MagicMock()))

try:  # pragma: no cover
    import dotenv  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    sys.modules.setdefault("dotenv", SimpleNamespace(load_dotenv=lambda: None))

try:  # pragma: no cover
    import langchain_openai  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    sys.modules.setdefault("langchain_openai", SimpleNamespace(ChatOpenAI=MagicMock()))

try:  # pragma: no cover
    import langchain_core.messages  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    sys.modules.setdefault(
        "langchain_core.messages",
        SimpleNamespace(
            HumanMessage=MagicMock,
            SystemMessage=MagicMock,
            BaseMessage=MagicMock,
        ),
    )

from commit_dude import cli
from commit_dude.schemas import CommitMessageResponse


class _FakeStdin:
    """Small helper providing a configurable ``stdin`` object."""

    def __init__(self, *, text: str, tty: bool):
        self._text = text
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty

    def read(self) -> str:
        return self._text


def _successful_response() -> CommitMessageResponse:
    return CommitMessageResponse(agent_response="agent", commit_message="commit msg")


def test_main_uses_stdin_diff_when_not_tty(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    diff_text = "some diff"
    monkeypatch.setattr(cli.sys, "stdin", _FakeStdin(text=diff_text, tty=False))
    mocked_copy = MagicMock()
    monkeypatch.setattr(cli.pyperclip, "copy", mocked_copy)

    captured_diff = {}

    def _fake_generate(diff: str) -> CommitMessageResponse:
        captured_diff["value"] = diff
        return _successful_response()

    monkeypatch.setattr(cli, "generate_commit_message", _fake_generate)

    cli.main.callback()

    captured = capsys.readouterr()
    assert "🤖 Generating commit message..." in captured.out
    assert "agent" in captured.out
    assert "commit msg" in captured.out
    assert captured_diff["value"] == diff_text
    mocked_copy.assert_called_once_with("commit msg")


def test_main_collects_git_diff_and_status_when_tty(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli.sys, "stdin", _FakeStdin(text="", tty=True))

    mocked_copy = MagicMock()
    monkeypatch.setattr(cli.pyperclip, "copy", mocked_copy)

    subprocess_calls = []

    def _fake_run(cmd, *, capture_output, text, check):
        subprocess_calls.append(cmd)
        mock_result = MagicMock()
        if cmd[:2] == ["git", "diff"]:
            mock_result.stdout = "diff output\n"
        elif cmd[:2] == ["git", "status"]:
            mock_result.stdout = " M tracked.txt\n"
        else:  # pragma: no cover - defensive guard
            raise AssertionError(f"Unexpected command: {cmd}")
        return mock_result

    monkeypatch.setattr(cli.subprocess, "run", _fake_run)

    observed_diff = {}

    def _fake_generate(diff: str) -> CommitMessageResponse:
        observed_diff["value"] = diff
        return _successful_response()

    monkeypatch.setattr(cli, "generate_commit_message", _fake_generate)

    cli.main.callback()

    capsys.readouterr()  # flush captured output (not asserted here)
    assert subprocess_calls == [
        ["git", "diff", "HEAD"],
        ["git", "status", "--porcelain"],
    ]
    # diff output is stripped and status is appended (without leading newline)
    assert observed_diff["value"] == "diff outputM tracked.txt"
    mocked_copy.assert_called_once_with("commit msg")


def test_main_exits_with_error_when_diff_empty(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli.sys, "stdin", _FakeStdin(text="", tty=False))

    with patch.object(cli, "generate_commit_message") as mocked_generate, patch.object(cli.pyperclip, "copy") as mocked_copy:
        with pytest.raises(SystemExit):
            cli.main.callback()

    captured = capsys.readouterr()
    assert "No changes detected" in captured.err
    mocked_generate.assert_not_called()
    mocked_copy.assert_not_called()


def test_main_surfaces_generation_errors(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli.sys, "stdin", _FakeStdin(text="something", tty=False))

    error = RuntimeError("boom")
    monkeypatch.setattr(cli, "generate_commit_message", MagicMock(side_effect=error))
    mocked_copy = MagicMock()
    monkeypatch.setattr(cli.pyperclip, "copy", mocked_copy)

    with pytest.raises(SystemExit):
        cli.main.callback()

    captured = capsys.readouterr()
    assert "Failed to generate commit message: boom" in captured.err
    mocked_copy.assert_not_called()
