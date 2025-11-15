from typing import Callable, Optional

import click
import pyperclip

from commit_dude.schemas import CommitMessageResponse
from commit_dude.settings import commit_dude_logger
from commit_dude.errors import TokenLimitExceededError

from .service import CommitDudeService

logger = commit_dude_logger(__name__)


class CommitDudeController:
    """Main controller orchestrating the CLI workflow."""

    def __init__(
        self,
        commit_dude_service: CommitDudeService,
        clipboard_copy: Callable[[str], None] = pyperclip.copy,
        echo: Callable[..., None] = click.echo,
        echo_err: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._clipboard_copy = clipboard_copy
        self._echo = echo
        self._echo_err = echo_err or (lambda message: self._echo(message, err=True))
        self.commit_dude_service = commit_dude_service

    # --- Public API ---
    def run(self) -> int:
        logger.debug("Starting CLI controller run")
        diff = self.commit_dude_service.read_diff()

        if not diff:
            logger.warning("No diff detected")
            self._echo_err("--- ❌ No changes detected. Add or modify files first. ---")
            return 1

        try:
            self._echo("🤖 Generating commit message...")
            result = self.commit_dude_service.generate_commit(diff)
            self._display_commit(result)
            return 0
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

        logger.debug("Displaying agent response and commit message")
        self._echo(agent_response)
        self._echo(commit_msg)

        logger.debug("Copying commit message to clipboard")
        self._clipboard_copy(commit_msg)
        self._echo("\n✅ Suggested commit message copied to clipboard.\n")
