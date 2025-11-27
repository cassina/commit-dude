import sys

import click

from commit_dude.core.settings import set_commit_dude_log_level
from commit_dude.core.agents import CommitDudeAgent

from .service import CommitDudeService
from .controller import CommitDudeController


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option(
    "--no-strict", is_flag=True, help="Enable 'redacted' commit generation strategy"
)
@click.option(
    "--model-provider",
    type=click.Choice(["openai", "local"], case_sensitive=False),
    default="openai",
    show_default=True,
    help="Choose between OpenAI (default) or a local Ollama model",
)
@click.option(
    "--local-model-id",
    type=str,
    default="llama3.2",
    show_default=True,
    help="Ollama model name to run locally",
)
@click.option(
    "--local-base-url",
    type=str,
    default=None,
    help="Custom Ollama base URL (defaults to localhost)",
)
def run_commit_dude(
    debug: bool,
    no_strict: bool = False,
    model_provider: str = "openai",
    local_model_id: str = "llama3.2",
    local_base_url: str | None = None,
):
    """Entry point for Commit Dude CLI."""
    if debug:
        set_commit_dude_log_level("DEBUG")

    strict = False if no_strict else True
    agent = CommitDudeAgent(
        strict=strict,
        model_provider=model_provider,
        local_model_id=local_model_id,
        local_base_url=local_base_url,
    )
    service = CommitDudeService(agent=agent)
    controller = CommitDudeController(service)

    sys.exit(controller.run())
