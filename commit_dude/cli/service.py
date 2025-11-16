import logging
import subprocess
import sys
from typing import Optional, TextIO, Sequence, Callable

from commit_dude.schemas import CommitMessageResponse
from commit_dude.core.factory import CommitDudeAgent
from commit_dude.settings import commit_dude_logger


class CommitDudeService:
    def __init__(
        self,
        agent: CommitDudeAgent,
        logger: Optional[logging.Logger] = None,
        stdin: TextIO = sys.stdin,
        run_process: Optional[
            Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
        ] = None,
        isatty: Optional[Callable[[], bool]] = None,
    ) -> None:
        self._logger = logger or commit_dude_logger(__name__)
        self._stdin = stdin
        self._isatty = isatty or stdin.isatty
        self._run_process = run_process or self._default_run_process
        self.agent = agent

    # --- Public API ---
    def read_diff(self) -> str:
        self._logger.debug("Collecting diff...")

        if not self._isatty():
            self._logger.debug("Reading diff from stdin...")
            return self._stdin.read().strip()

        diff_output = self._run_git_command(["git", "diff", "HEAD"])
        status_output = self._run_git_command(["git", "status", "--porcelain"])

        combined = "\n".join(
            part for part in [diff_output, status_output] if part
        ).strip()

        self._logger.debug("Combined diff length: %d", len(combined))

        return combined

    def generate_commit(self, diff: str) -> CommitMessageResponse:
        try:
            self._logger.debug("⛓️ Invoking Commit Dude agent...")
            result = self.agent.invoke(diff)
            self._logger.debug("⛓️ Invocation completed successfully.")
            return result["structured_response"]

        except Exception as error:
            raise error

    # --- Private helpers ---
    def _run_git_command(self, args: Sequence[str]) -> str:
        self._logger.debug("Running git command: %s", " ".join(args))
        result = self._run_process(args)
        stdout = result.stdout.strip()
        self._logger.debug("Git output length: %d", len(stdout))
        return stdout

    # --- Static helpers ---
    @staticmethod
    def _default_run_process(
        args: Sequence[str],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, capture_output=True, text=True, check=False)
