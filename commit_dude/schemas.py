from typing import Literal

from pydantic import BaseModel, field_validator

Strategy = Literal["block", "redact"]

class CommitMessageResponse(BaseModel):
    agent_response: str
    commit_message: str

    @field_validator("commit_message")
    @classmethod
    def enforce_line_length(cls, value: str) -> str:
        if not value:
            return value

        for line in value.splitlines():
            if len(line) > 100:
                raise ValueError(
                    f"The commit_message lines must be 100 characters or fewer, message: {value}"
                )

        return value
