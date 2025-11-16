import pytest
from pydantic import ValidationError

from commit_dude.core.factory import CommitDudeAgent
from commit_dude.schemas import CommitMessageResponse


def _make_agent() -> CommitDudeAgent:
    """Create an agent instance without running the heavy constructor."""

    return object.__new__(CommitDudeAgent)


def test_wrap_commit_message_reflows_headers():
    agent = _make_agent()
    message = "feat: add hyper-detailed explanation " + "and supporting rationale " * 5

    wrapped = agent._wrap_commit_message(message)

    lines = wrapped.splitlines()
    assert len(lines) > 1
    assert all(len(line) <= 100 for line in lines)


def test_wrap_commit_message_handles_bullets_and_blank_lines():
    agent = _make_agent()
    message = (
        "- "
        + "document every subtle nuance in excruciating detail " * 3
        + "\n\n"
        + "Provide a thorough justification that spans multiple sentences and contexts."
    )

    wrapped = agent._wrap_commit_message(message)
    lines = wrapped.splitlines()

    assert lines[0].startswith("- ")
    assert "" in lines  # blank line preserved between paragraphs
    assert all(len(line) <= 100 for line in lines if line)


def test_commit_message_response_rejects_long_lines():
    with pytest.raises(ValidationError):
        CommitMessageResponse(
            agent_response="Summarized diff",
            commit_message="a" * 101,
        )


def test_commit_message_response_accepts_wrapped_output():
    agent = _make_agent()
    overlong_message = (
        """feat: start detailed overview

Provide background """
        + "information " * 10
    )

    wrapped = agent._wrap_commit_message(overlong_message)

    response = CommitMessageResponse(
        agent_response="Summarized diff",
        commit_message=wrapped,
    )

    assert all(len(line) <= 100 for line in response.commit_message.splitlines())
