from pydantic import BaseModel


class CommitMessageResponse(BaseModel):
    agent_response: str
    commit_message: str


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
