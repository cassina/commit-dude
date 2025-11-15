import sys

import click


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--debug", is_flag=True, help="Enable debug logging")
def run_commit_dude(debug: bool):
    from commit_dude.settings import set_commit_dude_log_level
    from .service import CommitDudeService
    from .controller import CommitDudeController

    set_commit_dude_log_level("DEBUG") if debug else None
    service = CommitDudeService()
    controller = CommitDudeController(service)
    sys.exit(controller.run())
