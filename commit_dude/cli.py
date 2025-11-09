import sys
import subprocess

import click
import pyperclip

from commit_dude.llm import ChatCommitDude
from commit_dude.schemas import CommitMessageResponse


@click.command()
def main():
    if not sys.stdin.isatty():
        diff = sys.stdin.read().strip()
    else:
        cmd = ["git", "diff", "HEAD"]
        diff = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()

        # Ensure the diff is not empty
        diff += f"\n {status}".strip()

    if not diff:
        click.echo("--- ❌ No changes detected. Add or modify files first. ---", err=True)
        sys.exit(1)

    click.echo("🤖 Generating commit message...")

    try:
        new_commit_dude = ChatCommitDude()
        commit_response: CommitMessageResponse = new_commit_dude.invoke(diff)
    except Exception as exc:  # pragma: no cover - surface helpful message
        click.echo(f"❌ Failed to generate commit message: {exc}", err=True)
        sys.exit(1)

    commit_msg = commit_response.commit_message
    agent_response = commit_response.agent_response

    click.echo(agent_response)
    click.echo(commit_msg)

    pyperclip.copy(commit_msg)
    click.echo("\n✅ Suggested commit message copied to clipboard. \n")


if __name__ == "__main__":
    main()
