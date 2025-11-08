import sys
import subprocess
import click
import pyperclip
from commit_dude.schemas import CommitMessageResponse
from langchain_core.messages import ToolMessage

from .llm import generate_commit_message


@click.command()
def main():
    if not sys.stdin.isatty():
        diff = sys.stdin.read().strip()
    else:
        cmd = cmd = ["git", "diff", "HEAD"]
        diff = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        ).stdout.strip()

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
        ).stdout.strip()

        diff += f"\n {status}"

    if not diff:
        click.echo("❌ No changes detected. Add or modify files first.", err=True)
        sys.exit(1)

    click.echo("🤖 Generating commit message...")

    response = generate_commit_message(diff)

    try:
        commit_response: CommitMessageResponse = response["structured_response"]
        commit_msg = commit_response.commit_message
        agent_response = commit_response.agent_response

        click.echo(agent_response)
        click.echo(commit_msg)

        pyperclip.copy(commit_msg)
        click.echo("\n✅ Suggested commit message copied to clipboard. \n")
    except Exception as e:
        print(f"O shit! {e}")

    # Clean and copy only the commit msg to clipboard
    # clean_message = message.replace("\n", " ").replace("\r", "").strip('`')

