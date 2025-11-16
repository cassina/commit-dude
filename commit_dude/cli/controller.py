import logging
from typing import Callable, Optional

import click
import pyperclip

from commit_dude.schemas import CommitMessageResponse
from commit_dude.settings import commit_dude_logger
from commit_dude.errors import TokenLimitExceededError
from commit_dude.errors import SecretPatternDetectorError

from .service import CommitDudeService


class CommitDudeController:
    """Main controller orchestrating the CLI workflow."""

    def __init__(
        self,
        commit_dude_service: CommitDudeService,
        logger: Optional[logging.Logger] = None,
        clipboard_copy: Callable[[str], None] = pyperclip.copy,
        echo: Callable[..., None] = click.echo,
        echo_err: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._logger = logger or commit_dude_logger(__name__)
        self._clipboard_copy = clipboard_copy
        self._echo = echo
        self._echo_err = echo_err or (lambda message: self._echo(message, err=True))
        self.commit_dude_service = commit_dude_service

    # --- Public API ---
    def run(self) -> int:
        self._echo("🤖 Generating commit message... \n")
        self._logger.debug("Starting CLI controller run")
        diff = self.commit_dude_service.read_diff()

        if not diff:
            self._echo_err("--- ❌ No changes detected. Add or modify files first. ---")
            return 1

        try:
            result = self.commit_dude_service.generate_commit(diff)
            self._display_commit(result)
            return 0
        except SecretPatternDetectorError:
            self._echo_err(
                "Diff contains secret patterns. Blocking the request since strict mode is enabled."
            )
            return 1
        except TokenLimitExceededError:
            self._echo_err(
                f"Token limit exceeded. Try reducing the diff size of: {len(diff)}"
            )
            return 1
        except Exception as e:
            self._echo_err(f"An error occurred: {e}")
            return 1

    # --- Private helpers ---
    def _display_commit(self, commit_response: CommitMessageResponse) -> None:
        commit_msg = commit_response.commit_message
        agent_response = commit_response.agent_response

        self._logger.debug("Displaying agent response and commit message")
        self._echo(f"{agent_response} \n")
        self._echo(f"{commit_msg} \n")

        self._clipboard_copy(commit_msg)
        self._echo("\n✅ Suggested commit message copied to clipboard.\n")
