from pydantic import BaseModel, field_validator


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
                raise ValueError(f"The commit_message lines must be 100 characters or fewer, message: {value}")

        return value


class Result:
    def __init__(self, value=None, error_message=None):
        self.value = value
        self.error_message = error_message

    @staticmethod
    def ok(value):
        return Result(value=value)

    @staticmethod
    def err(msg):
        return Result(error_message=msg)

    def is_ok(self):
        return self.error_message is None

    def is_err(self):
        return not self.is_ok()
