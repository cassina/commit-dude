"""Command-line interface for Commit Dude."""
import sys
import subprocess
from typing import Callable, Optional, Sequence, TextIO

import click
import pyperclip

from commit_dude.llm import ChatCommitDude
from commit_dude.schemas import CommitMessageResponse
from commit_dude.settings import commit_dude_logger, set_commit_dude_log_level

logger = commit_dude_logger(__name__)


class CommitDudeCLI:
    """Handle diff collection and commit message generation for the CLI."""

    def __init__(
        self,
        stdin: TextIO = sys.stdin,
        run_process: Optional[
            Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
        ] = None,
        llm_factory: Callable[[], ChatCommitDude] = ChatCommitDude,
        clipboard_copy: Callable[[str], None] = pyperclip.copy,
        echo: Callable[..., None] = click.echo,
        echo_err: Optional[Callable[[str], None]] = None,
        isatty: Optional[Callable[[], bool]] = None,
        *,
        auto_mode: bool = False,
        add_paths: Sequence[str] | None = None,
    ) -> None:
        """Create a CLI handler with injectable dependencies for easy testing."""

        self._stdin = stdin
        self._run_process = run_process or self._default_run_process
        self._llm_factory = llm_factory
        self._clipboard_copy = clipboard_copy
        self._echo = echo
        self._echo_err = echo_err or (lambda message: self._echo(message, err=True))
        self._isatty = isatty or stdin.isatty
        self._auto_mode = auto_mode
        self._add_paths = tuple(add_paths or ())

    # --- Public API -----------------------------------------------------
    def run(self) -> int:
        """Execute the CLI workflow and return an exit code."""

        logger.debug("Starting CLI run")

        if self._auto_mode:
            logger.info("Running in auto mode with paths: %s", self._add_paths or (".",))
            return self._run_auto()

        diff = self._read_diff()

        if not diff:
            logger.warning("No diff detected")
            self._echo_err("--- ❌ No changes detected. Add or modify files first. ---")
            return 1

        self._echo("🤖 Generating commit message...")

        try:
            commit_response = self._create_commit_dude().invoke(diff)
        except Exception as exc:  # pragma: no cover - surface helpful message
            logger.exception("Failed to generate commit message")
            self._echo_err(f"❌ Failed to generate commit message: {exc}")
            return 1

        self._display_commit(commit_response)
        return 0

    # --- Internal helpers ----------------------------------------------
    def _run_auto(self) -> int:
        """Handle the automated staging and committing workflow."""

        diff = self._read_diff()

        if not diff:
            logger.warning("No diff detected before staging")
            self._echo_err("--- ❌ No changes detected. Add or modify files first. ---")
            return 1

        add_targets = self._add_paths or (".",)

        for target in add_targets:
            logger.info("Staging changes for target: %s", target)
            result = self._run_process(["git", "add", target])
            if result.returncode != 0:
                stderr = result.stderr.strip() if result.stderr else ""
                stdout = result.stdout.strip() if result.stdout else ""
                error_message = stderr or stdout or "Unknown git add error"
                logger.error("git add failed for %s: %s", target, error_message)
                self._echo_err(f"❌ Failed to stage changes for {target}: {error_message}")
                return 1

        status_after_add = self._run_git_command(["git", "status", "--porcelain"])
        if status_after_add:
            logger.debug("Status after staging: %s", status_after_add)
            self._echo("📄 git status after staging:\n" + status_after_add)
        else:
            logger.debug("Status after staging is clean")
            self._echo("📄 git status after staging: (clean)")

        combined_context = "\n".join(part for part in [diff, status_after_add] if part).strip()
        logger.debug("Auto mode combined context length: %d", len(combined_context))

        self._echo("🤖 Generating commit message...")

        try:
            commit_response = self._create_commit_dude().invoke(combined_context)
        except Exception as exc:  # pragma: no cover - surface helpful message
            logger.exception("Failed to generate commit message in auto mode")
            self._echo_err(f"❌ Failed to generate commit message: {exc}")
            return 1

        self._display_commit(commit_response, copy_to_clipboard=False)

        if not self._commit_with_message(commit_response.commit_message):
            return 1

        return 0

    def _read_diff(self) -> str:
        """Read a diff from stdin or git commands."""

        if not self._isatty():
            logger.debug("Reading diff from stdin")
            return self._stdin.read().strip()

        logger.debug("Collecting diff using git commands")
        diff_output = self._run_git_command(["git", "diff", "HEAD"])
        status_output = self._run_git_command(["git", "status", "--porcelain"])

        logger.debug(f"diff output: {diff_output}")
        logger.debug(f"status output: {status_output}")

        combined = "\n".join(
            part for part in [diff_output, status_output] if part
        ).strip()
        logger.debug("Combined diff length: %d", len(combined))

        logger.debug("Combined diff: %s", combined)
        return combined

    def _run_git_command(self, args: Sequence[str]) -> str:
        """Execute a git command and return its trimmed stdout."""

        logger.debug("Running command: %s", " ".join(args))
        result = self._run_process(args)
        if result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else ""
            stdout = result.stdout.strip() if result.stdout else ""
            logger.debug("Command returned non-zero exit code %s", result.returncode)
            if stderr or stdout:
                logger.debug("Command stderr/stdout: %s %s", stderr, stdout)
        stdout = result.stdout.strip()
        logger.debug("Command output length: %d", len(stdout))
        return stdout

    def _create_commit_dude(self) -> ChatCommitDude:
        """Instantiate the language model helper."""

        logger.debug("Creating ChatCommitDude instance via factory")
        return self._llm_factory()

    def _display_commit(
        self, commit_response: CommitMessageResponse, *, copy_to_clipboard: bool = True
    ) -> None:
        """Display the generated commit message and optionally copy it."""

        commit_msg = commit_response.commit_message
        agent_response = commit_response.agent_response

        logger.debug("Displaying agent response and commit message")
        self._echo(agent_response)
        self._echo(commit_msg)

        if copy_to_clipboard:
            logger.debug("Copying commit message to clipboard")
            self._clipboard_copy(commit_msg)
            self._echo("\n✅ Suggested commit message copied to clipboard. \n")

    def _commit_with_message(self, commit_message: str) -> bool:
        """Create a git commit using the generated commit message."""

        parts = [part.strip() for part in commit_message.strip().split("\n\n") if part.strip()]

        if not parts:
            logger.error("Generated commit message is empty")
            self._echo_err("❌ Generated commit message is empty. Aborting commit.")
            return False

        commit_command = ["git", "commit"]
        for part in parts:
            commit_command.extend(["-m", part])

        logger.info("Running git commit with generated message")
        result = self._run_process(commit_command)

        stderr = result.stderr.strip() if result.stderr else ""
        stdout = result.stdout.strip() if result.stdout else ""

        if result.returncode != 0:
            logger.error("git commit failed: %s", stderr or stdout)
            self._echo_err(f"❌ Failed to create commit: {stderr or stdout or 'Unknown git commit error'}")
            return False

        if stdout:
            self._echo(stdout)
        if stderr:
            self._echo_err(stderr)

        self._echo("✅ Commit created successfully.")
        return True

    # --- Static helpers -------------------------------------------------
    @staticmethod
    def _default_run_process(
        args: Sequence[str],
    ) -> subprocess.CompletedProcess[str]:
        """Execute a subprocess with standard CLI defaults."""

        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
        )


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option(
    "--auto",
    "-a",
    is_flag=True,
    help="Stage changes (optionally limited to provided paths) and commit automatically.",
)
@click.argument("paths", nargs=-1)
def main(debug: bool, auto: bool, paths: tuple[str, ...]) -> None:
    """Generate commit messages from staged changes or piped diffs.

    \b
    Workflow:
      1. When run without piped input, Commit Dude calls:
         - git diff HEAD
         - git status --porcelain
         and combines their output.
      2. When diff text is piped to stdin, that input is used instead of git.
      3. The generated commit message is printed and copied to the clipboard.
      4. With --auto/--a, Commit Dude stages the provided paths (or everything)
         and creates a commit using the generated message.

    Usage:
      commit-dude [--debug] [--auto|-a] [PATH...]
      git diff --staged | commit-dude

    Options:
      --debug         Enable debug logging for troubleshooting.
      --auto, -a      Stage changes and create a commit automatically.
      -h, --help      Show this message and exit.

    Environment:
      Provide an OPENAI_API_KEY via environment variable or a .env file.
    """
    if debug:
        set_commit_dude_log_level("DEBUG")
        logger.debug("Debug logging enabled via --debug flag")

    if not auto and paths:
        raise click.UsageError("Paths can only be provided when using --auto/--a.")

    cli_kwargs: dict[str, object] = {}

    if auto:
        cli_kwargs["auto_mode"] = True
        if paths:
            cli_kwargs["add_paths"] = paths

    cli = CommitDudeCLI(**cli_kwargs)
    sys.exit(cli.run())



if __name__ == "__main__":
    main()
