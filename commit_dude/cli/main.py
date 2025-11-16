import sys

import click

from commit_dude.settings import set_commit_dude_log_level
from commit_dude.core.factory import CommitDudeAgent

from .service import CommitDudeService
from .controller import CommitDudeController


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--no-strict", is_flag=True, help="Enable 'redacted' commit generation strategy")
def run_commit_dude(debug: bool, no_strict: bool = False):
    """Entry point for Commit Dude CLI."""
    if debug:
        set_commit_dude_log_level("DEBUG")

    strict = False if no_strict else True
    agent = CommitDudeAgent(strict=strict)
    service = CommitDudeService(agent=agent)
    controller = CommitDudeController(service)

    sys.exit(controller.run())
