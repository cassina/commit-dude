#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the Commit Dude CLI."""

import logging
import subprocess
from typing import Any, List, Sequence

import pytest

from click.testing import CliRunner

import click
import pyperclip

from commit_dude.cli import CommitDudeCLI, ChatCommitDude, main
from commit_dude.schemas import CommitMessageResponse


class FakeStdin:
    """Simple stdin stub with configurable content and TTY flag."""

    def __init__(self, content: str = "", *, isatty: bool = False) -> None:
        self._content = content
        self._isatty = isatty
        self.read_calls = 0

    def read(self) -> str:
        self.read_calls += 1
        return self._content

    def isatty(self) -> bool:
        return self._isatty


class FakeLLM:
    """LLM stub that records invoke calls and returns predefined responses."""

    def __init__(self, response: CommitMessageResponse, *, should_raise: bool = False) -> None:
        self.response = response
        self.should_raise = should_raise
        self.invocations: List[str] = []

    def invoke(self, diff: str) -> CommitMessageResponse:
        self.invocations.append(diff)
        if self.should_raise:
            raise RuntimeError("boom")
        return self.response


class DummyChatCommitDude(ChatCommitDude):
    """Minimal ChatCommitDude subclass for factory testing."""

    def __init__(self) -> None:  # pragma: no cover - behavior irrelevant
        # Intentionally bypass parent initialization to avoid network setup.
        pass


def _completed_process(output: str) -> subprocess.CompletedProcess[str]:
    """Helper to build subprocess results with provided stdout."""

    return subprocess.CompletedProcess(args=["git"], returncode=0, stdout=output, stderr="")


# === Initialization ======================================================


def test_init_uses_default_dependencies():
    """CLI should fall back to default helpers when none provided."""

    stdin = FakeStdin()
    cli = CommitDudeCLI(stdin=stdin)

    assert cli._run_process is CommitDudeCLI._default_run_process
    assert cli._llm_factory is ChatCommitDude
    assert cli._clipboard_copy is pyperclip.copy
    assert cli._echo is click.echo


def test_init_accepts_custom_injected_dependencies():
    """Supplied dependencies must be preserved on the instance."""

    stdin = FakeStdin()

    def custom_run_process(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return _completed_process("")

    def custom_factory() -> str:
        return "llm"

    def custom_clipboard(value: str) -> None:
        return None

    def custom_echo(message: str, **_: Any) -> None:
        return None

    def custom_echo_err(message: str) -> None:
        return None

    def custom_isatty() -> bool:
        return True

    cli = CommitDudeCLI(
        stdin=stdin,
        run_process=custom_run_process,
        llm_factory=custom_factory,  # type: ignore[arg-type]
        clipboard_copy=custom_clipboard,
        echo=custom_echo,
        echo_err=custom_echo_err,
        isatty=custom_isatty,
    )

    assert cli._run_process is custom_run_process
    assert cli._llm_factory is custom_factory
    assert cli._clipboard_copy is custom_clipboard
    assert cli._echo is custom_echo
    assert cli._echo_err is custom_echo_err
    assert cli._isatty is custom_isatty


def test_init_sets_echo_err_default_when_not_provided():
    """When echo_err omitted, CLI should wrap echo with err=True."""

    captured: list[tuple[str, dict[str, Any]]] = []

    def fake_echo(message: str, **kwargs: Any) -> None:
        captured.append((message, kwargs))

    cli = CommitDudeCLI(stdin=FakeStdin(), echo=fake_echo)

    cli._echo_err("problem")

    assert captured == [("problem", {"err": True})]


def test_init_sets_isatty_default_to_stdin_isatty():
    """Default TTY detector should reference stdin.isatty when not provided."""

    stdin = FakeStdin(isatty=True)

    cli = CommitDudeCLI(stdin=stdin)

    assert cli._isatty() is True
    assert getattr(cli._isatty, "__self__", None) is stdin


# === Public API: run() ==================================================


def test_run_returns_1_when_no_diff_detected():
    """Empty diffs should yield exit code 1 and display a helpful message."""

    errors: list[str] = []

    def fail_factory() -> None:  # pragma: no cover - sanity guard
        raise AssertionError("LLM should not be constructed when diff missing")

    cli = CommitDudeCLI(
        stdin=FakeStdin("   \n", isatty=False),
        llm_factory=fail_factory,  # type: ignore[arg-type]
        echo=lambda *_args, **_kwargs: None,
        echo_err=lambda message: errors.append(message),
        isatty=lambda: False,
    )

    exit_code = cli.run()

    assert exit_code == 1
    assert errors[-1] == "--- ❌ No changes detected. Add or modify files first. ---"


def test_run_reads_diff_from_stdin_when_not_tty():
    """When stdin is not a TTY the diff should be sourced from stdin.read()."""

    response = CommitMessageResponse(agent_response="ok", commit_message="feat: msg")
    fake_llm = FakeLLM(response)

    cli = CommitDudeCLI(
        stdin=FakeStdin(" diff content \n", isatty=False),
        llm_factory=lambda: fake_llm,
        echo=lambda *_args, **_kwargs: None,
        echo_err=lambda *_args, **_kwargs: None,
        clipboard_copy=lambda *_args, **_kwargs: None,
        run_process=lambda _args: (_ for _ in ()).throw(AssertionError("git should not run")),
        isatty=lambda: False,
    )

    assert cli.run() == 0
    assert fake_llm.invocations == ["diff content"]


def test_run_reads_diff_from_git_when_tty():
    """TTY input should trigger git commands to assemble the diff."""

    response = CommitMessageResponse(agent_response="ok", commit_message="feat: msg")
    fake_llm = FakeLLM(response)

    outputs = iter(["diff-output\n", "status-output\n"])

    def fake_run_process(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return _completed_process(next(outputs))

    cli = CommitDudeCLI(
        stdin=FakeStdin("", isatty=True),
        run_process=fake_run_process,
        llm_factory=lambda: fake_llm,
        echo=lambda *_args, **_kwargs: None,
        echo_err=lambda *_args, **_kwargs: None,
        clipboard_copy=lambda *_args, **_kwargs: None,
        isatty=lambda: True,
    )

    assert cli.run() == 0
    assert fake_llm.invocations == ["diff-output\nstatus-output"]


def test_run_calls_invoke_and_displays_commit_message():
    """The CLI should display generated messages and copy the commit to clipboard."""

    response = CommitMessageResponse(
        agent_response="Agent says hi", commit_message="feat: greet"
    )
    fake_llm = FakeLLM(response)
    echoes: list[str] = []
    clipboard: list[str] = []

    cli = CommitDudeCLI(
        stdin=FakeStdin("diff", isatty=False),
        llm_factory=lambda: fake_llm,
        echo=lambda message, **_: echoes.append(message),
        echo_err=lambda message: pytest.fail(f"Unexpected error echo: {message}"),
        clipboard_copy=lambda value: clipboard.append(value),
        isatty=lambda: False,
    )

    assert cli.run() == 0
    assert fake_llm.invocations == ["diff"]
    assert clipboard == ["feat: greet"]
    assert "Agent says hi" in echoes
    assert "feat: greet" in echoes
    assert "🤖 Generating commit message..." in echoes
    assert "✅ Suggested commit message copied to clipboard." in "".join(echoes)


def test_run_handles_llm_exceptions_and_returns_1():
    """Any exception from the LLM should be surfaced and exit code 1 returned."""

    errors: list[str] = []

    def failing_factory() -> FakeLLM:
        return FakeLLM(
            CommitMessageResponse(agent_response="", commit_message=""),
            should_raise=True,
        )

    cli = CommitDudeCLI(
        stdin=FakeStdin("diff", isatty=False),
        llm_factory=failing_factory,  # type: ignore[arg-type]
        echo=lambda *_args, **_kwargs: None,
        echo_err=lambda message: errors.append(message),
        clipboard_copy=lambda *_args, **_kwargs: None,
        isatty=lambda: False,
    )

    assert cli.run() == 1
    assert any("Failed to generate commit message" in msg for msg in errors)


def test_run_logs_start_and_completion_messages(caplog: pytest.LogCaptureFixture):
    """Run should emit helpful debug logs for tracing."""

    caplog.set_level(logging.DEBUG, logger="commit_dude.cli")

    response = CommitMessageResponse(agent_response="ok", commit_message="feat: msg")
    fake_llm = FakeLLM(response)

    cli = CommitDudeCLI(
        stdin=FakeStdin("diff", isatty=False),
        llm_factory=lambda: fake_llm,
        echo=lambda *_args, **_kwargs: None,
        echo_err=lambda *_args, **_kwargs: None,
        clipboard_copy=lambda *_args, **_kwargs: None,
        isatty=lambda: False,
    )

    assert cli.run() == 0
    logged_messages = " ".join(record.message for record in caplog.records)
    assert "Starting CLI run" in logged_messages
    assert "Copying commit message to clipboard" in logged_messages


def test_run_echoes_user_feedback_messages():
    """User facing echoes should include progress and generated content."""

    response = CommitMessageResponse(
        agent_response="Agent feedback", commit_message="feat: feedback"
    )
    fake_llm = FakeLLM(response)
    echoes: list[str] = []

    cli = CommitDudeCLI(
        stdin=FakeStdin("diff", isatty=False),
        llm_factory=lambda: fake_llm,
        echo=lambda message, **_: echoes.append(message),
        echo_err=lambda message: pytest.fail(f"Unexpected error echo: {message}"),
        clipboard_copy=lambda *_args, **_kwargs: None,
        isatty=lambda: False,
    )

    assert cli.run() == 0
    assert echoes[0] == "🤖 Generating commit message..."
    assert "Agent feedback" in echoes
    assert "feat: feedback" in echoes
    assert echoes[-1].strip() == "✅ Suggested commit message copied to clipboard."


# === Internal Helpers: _read_diff() =======================================


def test_read_diff_reads_from_stdin_if_not_tty():
    """_read_diff should use stdin when not attached to a TTY."""

    stdin = FakeStdin(" diff contents \n", isatty=False)
    cli = CommitDudeCLI(
        stdin=stdin,
        isatty=lambda: False,
        echo=lambda *_args, **_kwargs: None,
        echo_err=lambda *_args, **_kwargs: None,
    )

    diff = cli._read_diff()

    assert diff == "diff contents"
    assert stdin.read_calls == 1


def test_read_diff_calls_git_commands_if_tty():
    """_read_diff should invoke git helpers when stdin is a TTY."""

    called: list[Sequence[str]] = []

    def fake_run_process(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        called.append(tuple(args))
        return _completed_process("")

    cli = CommitDudeCLI(
        stdin=FakeStdin("", isatty=True),
        run_process=fake_run_process,
        isatty=lambda: True,
        echo=lambda *_args, **_kwargs: None,
        echo_err=lambda *_args, **_kwargs: None,
    )

    cli._read_diff()

    assert called == [
        ("git", "diff", "HEAD"),
        ("git", "status", "--porcelain"),
    ]


def test_read_diff_combines_diff_and_status_outputs():
    """_read_diff should concatenate diff and status outputs with a newline."""

    outputs = iter(["diff-output\n", "status-output\n"])

    def fake_run_process(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return _completed_process(next(outputs))

    cli = CommitDudeCLI(
        stdin=FakeStdin("", isatty=True),
        run_process=fake_run_process,
        isatty=lambda: True,
        echo=lambda *_args, **_kwargs: None,
        echo_err=lambda *_args, **_kwargs: None,
    )

    diff = cli._read_diff()

    assert diff == "diff-output\nstatus-output"


def test_read_diff_returns_empty_string_if_no_changes():
    """_read_diff should return an empty string when git reports no changes."""

    outputs = iter(["", ""])

    def fake_run_process(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return _completed_process(next(outputs))

    cli = CommitDudeCLI(
        stdin=FakeStdin("", isatty=True),
        run_process=fake_run_process,
        isatty=lambda: True,
        echo=lambda *_args, **_kwargs: None,
        echo_err=lambda *_args, **_kwargs: None,
    )

    diff = cli._read_diff()

    assert diff == ""


# === Internal Helpers: _display_commit() ====================================


def test_display_commit_echoes_agent_and_message():
    """_display_commit should echo the agent response and commit message."""

    response = CommitMessageResponse(
        agent_response="Agent response", commit_message="feat: example"
    )
    echoes: list[str] = []

    cli = CommitDudeCLI(
        stdin=FakeStdin(),
        echo=lambda message, **_: echoes.append(message),
        echo_err=lambda *_args, **_kwargs: None,
        clipboard_copy=lambda *_args, **_kwargs: None,
        isatty=lambda: False,
    )

    cli._display_commit(response)

    assert response.agent_response in echoes
    assert response.commit_message in echoes


def test_display_commit_copies_message_to_clipboard():
    """_display_commit should copy the commit message to the clipboard."""

    response = CommitMessageResponse(
        agent_response="ignored", commit_message="feat: clipboard"
    )
    clipboard: list[str] = []

    cli = CommitDudeCLI(
        stdin=FakeStdin(),
        echo=lambda *_args, **_kwargs: None,
        echo_err=lambda *_args, **_kwargs: None,
        clipboard_copy=lambda value: clipboard.append(value),
        isatty=lambda: False,
    )

    cli._display_commit(response)

    assert clipboard == ["feat: clipboard"]


def test_display_commit_echoes_confirmation_message():
    """_display_commit should emit the confirmation banner after copying."""

    response = CommitMessageResponse(
        agent_response="agent", commit_message="feat: confirm"
    )
    echoes: list[str] = []

    cli = CommitDudeCLI(
        stdin=FakeStdin(),
        echo=lambda message, **_: echoes.append(message),
        echo_err=lambda *_args, **_kwargs: None,
        clipboard_copy=lambda *_args, **_kwargs: None,
        isatty=lambda: False,
    )

    cli._display_commit(response)

    assert echoes[-1].strip() == "✅ Suggested commit message copied to clipboard."


def test_display_commit_logs_actions(caplog: pytest.LogCaptureFixture):
    """_display_commit should log its key actions for observability."""

    caplog.set_level(logging.DEBUG, logger="commit_dude.cli")
    response = CommitMessageResponse(
        agent_response="agent", commit_message="feat: log"
    )

    cli = CommitDudeCLI(
        stdin=FakeStdin(),
        echo=lambda *_args, **_kwargs: None,
        echo_err=lambda *_args, **_kwargs: None,
        clipboard_copy=lambda *_args, **_kwargs: None,
        isatty=lambda: False,
    )

    cli._display_commit(response)

    messages = " ".join(record.message for record in caplog.records)
    assert "Displaying agent response and commit message" in messages
    assert "Copying commit message to clipboard" in messages


# === Static Helpers: _default_run_process() ================================


def test_default_run_process_returns_completed_process(monkeypatch):
    """_default_run_process should return the subprocess result."""

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout="output", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = CommitDudeCLI._default_run_process(["git", "status"])

    assert isinstance(result, subprocess.CompletedProcess)
    assert result.stdout == "output"


def test_default_run_process_captures_output_and_text(monkeypatch):
    """_default_run_process should request captured, text-mode output."""

    captured: dict[str, Any] = {}

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    CommitDudeCLI._default_run_process(["git", "diff"])

    assert captured["args"] == (["git", "diff"],)
    assert captured["kwargs"] == {
        "capture_output": True,
        "text": True,
        "check": False,
    }


# === CLI Entrypoint: main() ===============================================


def test_main_invokes_commitdudecli_run_and_exits(monkeypatch: pytest.MonkeyPatch):
    """main() should construct CommitDudeCLI, invoke run, and exit."""

    instances: list["FakeCLI"] = []

    class FakeCLI:
        def __init__(self) -> None:
            self.run_calls = 0
            instances.append(self)

        def run(self) -> int:
            self.run_calls += 1
            return 0

    monkeypatch.setattr("commit_dude.cli.CommitDudeCLI", FakeCLI)

    result = CliRunner().invoke(main)

    assert result.exit_code == 0
    assert len(instances) == 1
    assert instances[0].run_calls == 1


def test_main_returns_exit_code_0_on_success(monkeypatch: pytest.MonkeyPatch):
    """main() should propagate a zero exit code when run succeeds."""

    class SuccessfulCLI:
        def run(self) -> int:
            return 0

    monkeypatch.setattr("commit_dude.cli.CommitDudeCLI", SuccessfulCLI)

    result = CliRunner().invoke(main)

    assert result.exit_code == 0


def test_main_returns_exit_code_1_on_failure(monkeypatch: pytest.MonkeyPatch):
    """main() should return exit code 1 when the CLI run fails."""

    class FailingCLI:
        def run(self) -> int:
            return 1

    monkeypatch.setattr("commit_dude.cli.CommitDudeCLI", FailingCLI)

    result = CliRunner().invoke(main)

    assert result.exit_code == 1


# === Internal Helpers: _run_git_command() ================================


def test_run_git_command_executes_process_and_returns_stdout():
    """_run_git_command should delegate to the injected process runner."""

    recorded: list[Sequence[str]] = []

    def fake_run_process(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        recorded.append(tuple(args))
        return _completed_process("output")

    cli = CommitDudeCLI(
        stdin=FakeStdin(),
        run_process=fake_run_process,
        isatty=lambda: False,
        echo=lambda *_args, **_kwargs: None,
        echo_err=lambda *_args, **_kwargs: None,
    )

    result = cli._run_git_command(["git", "status"])

    assert result == "output"
    assert recorded == [("git", "status")]


def test_run_git_command_strips_trailing_newlines():
    """_run_git_command should trim whitespace from command output."""

    cli = CommitDudeCLI(
        stdin=FakeStdin(),
        run_process=lambda _args: _completed_process("value\n\n"),
        isatty=lambda: False,
        echo=lambda *_args, **_kwargs: None,
        echo_err=lambda *_args, **_kwargs: None,
    )

    result = cli._run_git_command(["git", "diff"])

    assert result == "value"


def test_run_git_command_logs_command_execution(caplog: pytest.LogCaptureFixture):
    """_run_git_command should log the command being executed."""

    caplog.set_level(logging.DEBUG, logger="commit_dude.cli")

    cli = CommitDudeCLI(
        stdin=FakeStdin(),
        run_process=lambda _args: _completed_process("ok"),
        isatty=lambda: False,
        echo=lambda *_args, **_kwargs: None,
        echo_err=lambda *_args, **_kwargs: None,
    )

    cli._run_git_command(["git", "status"])

    log_text = " ".join(record.message for record in caplog.records)
    assert "Running command: git status" in log_text
    assert "Command output length" in log_text


# === Internal Helpers: _create_commit_dude() =============================


def test_create_commit_dude_uses_llm_factory():
    """_create_commit_dude should invoke the configured factory exactly once."""

    calls = []

    def fake_factory() -> str:
        calls.append("called")
        return "llm"

    cli = CommitDudeCLI(
        stdin=FakeStdin(),
        llm_factory=fake_factory,  # type: ignore[arg-type]
        echo=lambda *_args, **_kwargs: None,
        echo_err=lambda *_args, **_kwargs: None,
    )

    result = cli._create_commit_dude()

    assert calls == ["called"]
    assert result == "llm"


def test_create_commit_dude_returns_chatcommitdude_instance():
    """_create_commit_dude should return the object produced by the factory."""

    cli = CommitDudeCLI(
        stdin=FakeStdin(),
        llm_factory=lambda: DummyChatCommitDude(),
        echo=lambda *_args, **_kwargs: None,
        echo_err=lambda *_args, **_kwargs: None,
    )

    commit_dude = cli._create_commit_dude()

    assert isinstance(commit_dude, ChatCommitDude)
    assert isinstance(commit_dude, DummyChatCommitDude)

