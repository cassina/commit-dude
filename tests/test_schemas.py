import pytest
from pydantic import ValidationError

from commit_dude.schemas import CommitMessageResponse


def test_commit_message_response_valid_payload():
    payload = {
        "agent_response": "Summarized diff",
        "commit_message": "feat: add new feature",
    }

    response = CommitMessageResponse(**payload)

    assert response.agent_response == payload["agent_response"]
    assert response.commit_message == payload["commit_message"]
    assert response.model_dump() == payload


@pytest.mark.parametrize("missing_field", ["agent_response", "commit_message"])
def test_commit_message_response_requires_fields(missing_field):
    payload = {
        "agent_response": "Summarized diff",
        "commit_message": "feat: add new feature",
    }
    payload.pop(missing_field)

    with pytest.raises(ValidationError):
        CommitMessageResponse(**payload)


@pytest.mark.parametrize("field", ["agent_response", "commit_message"])
def test_commit_message_response_rejects_none(field):
    payload = dict(
        agent_response="Summarized diff",
        commit_message="feat: add new feature"
    )
    payload[field] = None

    with pytest.raises(ValidationError):
        CommitMessageResponse(**payload)


def test_commit_message_response_ignores_extra_fields():
    response = CommitMessageResponse(
        agent_response="Summarized diff",
        commit_message="feat: add new feature",
        extra_field="ignored value",
    )

    assert not hasattr(response, "extra_field")
    assert response.model_dump() == {
        "agent_response": "Summarized diff",
        "commit_message": "feat: add new feature",
    }
