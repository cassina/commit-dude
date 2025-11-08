from pydantic import BaseModel


class CommitMessageResponse(BaseModel):
    agent_response: str
    commit_message: str