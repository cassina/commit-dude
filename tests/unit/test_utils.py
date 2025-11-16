import textwrap

from commit_dude.utils import wrap_commit_message


def test_wrap_commit_message_handles_bullet_lists_individually():
    first_bullet = "- " + "a" * 140
    second_bullet = "- " + "b" * 120
    wrapped = wrap_commit_message(f"{first_bullet}\n{second_bullet}")

    lines = wrapped.splitlines()

    bullet_lines = [line for line in lines if line.startswith("- ")]
    assert len(bullet_lines) == 2
    assert all(len(line) <= 100 for line in lines if line)


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
    assert all(len(line) <= 100 for line in lines if line)
