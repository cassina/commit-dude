"""Command-line interface for Commit Dude."""

import sys
import subprocess
from typing import Callable, Optional, Sequence, TextIO

import click
import pyperclip

from commit_dude.llm import ChatCommitDude
from commit_dude.schemas import CommitMessageResponse
from commit_dude.settings import commit_dude_logger

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
    ) -> None:
        """Create a CLI handler with injectable dependencies for easy testing."""

        self._stdin = stdin
        self._run_process = run_process or self._default_run_process
        self._llm_factory = llm_factory
        self._clipboard_copy = clipboard_copy
        self._echo = echo
        self._echo_err = echo_err or (lambda message: self._echo(message, err=True))
        self._isatty = isatty or stdin.isatty

    # --- Public API -----------------------------------------------------
    def run(self) -> int:
        """Execute the CLI workflow and return an exit code."""

        logger.debug("Starting CLI run")
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
    def _read_diff(self) -> str:
        """Read a diff from stdin or git commands."""

        if not self._isatty():
            logger.debug("Reading diff from stdin")
            return self._stdin.read().strip()

        logger.debug("Collecting diff using git commands")
        diff_output = self._run_git_command(["git", "diff", "HEAD"])
        status_output = self._run_git_command(["git", "status", "--porcelain"])

        combined = "\n".join(
            part for part in [diff_output, status_output] if part
        ).strip()
        logger.debug("Combined diff length: %d", len(combined))
        return combined

    def _run_git_command(self, args: Sequence[str]) -> str:
        """Execute a git command and return its trimmed stdout."""

        logger.debug("Running command: %s", " ".join(args))
        result = self._run_process(args)
        stdout = result.stdout.strip()
        logger.debug("Command output length: %d", len(stdout))
        return stdout

    def _create_commit_dude(self) -> ChatCommitDude:
        """Instantiate the language model helper."""

        logger.debug("Creating ChatCommitDude instance via factory")
        return self._llm_factory()

    def _display_commit(self, commit_response: CommitMessageResponse) -> None:
        """Display the generated commit message and copy it to the clipboard."""

        commit_msg = commit_response.commit_message
        agent_response = commit_response.agent_response

        logger.debug("Displaying agent response and commit message")
        self._echo(agent_response)
        self._echo(commit_msg)

        logger.debug("Copying commit message to clipboard")
        self._clipboard_copy(commit_msg)
        self._echo("\n✅ Suggested commit message copied to clipboard. \n")

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


@click.command()
def main() -> None:
    """Entry point used by the console script."""

    cli = CommitDudeCLI()
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
