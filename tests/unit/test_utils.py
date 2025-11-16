import textwrap

from commit_dude.config import COMMIT_LINE_LENGTH
from commit_dude.utils import wrap_commit_message


def test_wrap_commit_message_handles_bullet_lists_individually():
    first_bullet = "- " + "a" * 140
    second_bullet = "- " + "b" * 120
    wrapped = wrap_commit_message(f"{first_bullet}\n{second_bullet}")

    lines = wrapped.splitlines()

    bullet_lines = [line for line in lines if line.startswith("- ")]
    assert len(bullet_lines) == 2
    assert all(len(line) <= COMMIT_LINE_LENGTH for line in lines if line)


def test_wrap_commit_message_preserves_paragraph_breaks():
    paragraph = textwrap.dedent(
        """
        This is a fairly long paragraph that should be wrapped once it exceeds the maximum width but
        it should remain together as a single paragraph regardless of the original line breaks.
        """
    ).strip()
    message = (
        f"{paragraph}\n\nAnother paragraph that should stay separated by a blank line."
    )

    wrapped = wrap_commit_message(message)
    lines = wrapped.splitlines()

    assert "" in lines  # blank line separating the paragraphs
    assert all(len(line) <= COMMIT_LINE_LENGTH for line in lines if line)


def test_wrap_commit_message_wraps_breaking_change_footer():
    message = textwrap.dedent(
        """
        refactor(core)!: reorganize modules and update imports

        - rename commit_dude/core/factory.py -> commit_dude/core/agents.py
        - move commit_dude/utils.py -> commit_dude/core/utils.py
        - update imports in cli, service, middleware, and tests
        - add empty commit_dude/shared package

        BREAKING CHANGE: update external imports: commit_dude.core.factory -> commit_dude.core.agents; commit_dude.utils -> commit_dude.core.utils
        """
    ).strip()

    wrapped = wrap_commit_message(message, max_len=COMMIT_LINE_LENGTH)
    lines = wrapped.splitlines()

    assert any(line.startswith("BREAKING CHANGE:") for line in lines)
    assert all(len(line) <= COMMIT_LINE_LENGTH for line in lines if line)
