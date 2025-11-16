import textwrap
from typing import List


BULLET_PREFIXES = ("- ", "* ", "+ ")


def wrap_commit_message(commit_message: str) -> str:
    """Wrap commit messages so that no line exceeds 100 characters."""

    if commit_message is None:
        return commit_message

    wrapped_lines: List[str] = []
    paragraph_lines: List[str] = []

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return

        paragraph = " ".join(line.strip() for line in paragraph_lines).strip()
        if paragraph:
            wrapped_lines.extend(textwrap.wrap(paragraph, width=100) or [""])
        else:
            wrapped_lines.append("")
        paragraph_lines.clear()

    for line in commit_message.splitlines():
        stripped = line.lstrip()
        if not stripped:
            flush_paragraph()
            wrapped_lines.append("")
            continue

        indent = line[: len(line) - len(stripped)]
        bullet_prefix = next(
            (prefix for prefix in BULLET_PREFIXES if stripped.startswith(prefix)),
            None,
        )

        if bullet_prefix is not None:
            flush_paragraph()
            body = stripped[len(bullet_prefix) :].strip()
            initial_indent = indent + bullet_prefix
            subsequent_indent = indent + " " * len(bullet_prefix)
            wrapped_lines.extend(
                textwrap.wrap(
                    body,
                    width=100,
                    initial_indent=initial_indent,
                    subsequent_indent=subsequent_indent,
                )
                or [initial_indent.rstrip()]
            )
            continue

        paragraph_lines.append(line)

    flush_paragraph()

    return "\n".join(wrapped_lines)
