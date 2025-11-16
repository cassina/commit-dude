import textwrap
from typing import List


def wrap_commit_message(commit_message: str) -> str:
    """Wrap each paragraph to ensure no line exceeds 100 characters."""

    if not commit_message:
        return commit_message

    wrapped_lines: List[str] = []
    for paragraph in split_paragraphs(commit_message):
        if paragraph == "":
            wrapped_lines.append("")
            continue

        bullet_prefix = ""
        body = paragraph
        for prefix in ("- ", "* ", "+ "):
            if paragraph.startswith(prefix):
                bullet_prefix = prefix
                body = paragraph[len(prefix):].strip()
                break

        if bullet_prefix:
            wrapped = textwrap.wrap(
                body,
                width=100,
                initial_indent=bullet_prefix,
                subsequent_indent=" " * len(bullet_prefix),
            )
        else:
            wrapped = textwrap.wrap(paragraph, width=100)

        wrapped_lines.extend(wrapped or [""])

    return "\n".join(wrapped_lines)

def split_paragraphs(commit_message: str) -> List[str]:
    paragraphs: List[str] = []
    if commit_message is None:
        return paragraphs

    current_lines: List[str] = []
    for line in commit_message.splitlines():
        if not line.strip():
            if current_lines:
                paragraphs.append(" ".join(current_lines).strip())
                current_lines = []
            paragraphs.append("")
            continue

        current_lines.append(line.strip())

    if current_lines:
        paragraphs.append(" ".join(current_lines).strip())

    return paragraphs