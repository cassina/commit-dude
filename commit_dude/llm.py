import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt.chat_agent_executor import AgentStateWithStructuredResponsePydantic

from commit_dude.config import SYSTEM_PROMPT, MAX_TOKENS
from commit_dude.schemas import CommitMessageResponse

# Load .env automatically
load_dotenv()

def generate_commit_message(diff: str) -> str:
    """Send the git diff to an LLM and return a Conventional Commit message."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY. Set it in your .env file.")

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
        agent = create_agent(
            model=llm,
            system_prompt=SYSTEM_PROMPT,
            response_format=CommitMessageResponse,
        )

        num_tokens = llm.get_num_tokens(diff)
        print(f"Num tokens: {num_tokens}")
        if num_tokens > MAX_TOKENS:
            raise ValueError(f"Diff is too long. Max tokens: {MAX_TOKENS}, diff tokens: {num_tokens}")

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Please create a commit for this Git diff my dude:\n{diff}")
        ]

        # result = llm.invoke(messages)
        result = agent.invoke({"messages": messages})
        # print(result)
        return result
    except Exception as e:
        print(f"Error: {e}")
        raise e
