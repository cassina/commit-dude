import os
from typing import List, Type, Optional, Union, Callable

from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.runnables import Runnable
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage

from commit_dude.settings import logger
from commit_dude.schemas import CommitMessageResponse
from commit_dude.config import SYSTEM_PROMPT, MAX_TOKENS

# Load .env automatically
load_dotenv()


class ChatCommitDude:
    def __init__(
        self, 
        model: str = "gpt-4o-mini", 
        output: Type[BaseModel] = CommitMessageResponse,
        llm: Optional[Union[ChatOpenAI, BaseChatModel]] = None,
        structured_llm: Optional[Runnable] = None,
        get_env: Callable[[str], Optional[str]] = os.getenv,
        max_tokens: int = MAX_TOKENS,
        validate_api_key: bool = True
    ) -> None:
        logger.debug(f"Initializing ChatCommitDude with model: {model}")
        self.model: str = model
        self.output: Type[BaseModel] = output
        self.get_env: Callable[[str], Optional[str]] = get_env
        self.max_tokens: int = max_tokens
        
        if validate_api_key:
            self._validate_api_key()
        
        # Use injected dependencies or create defaults
        self.llm: Union[ChatOpenAI, BaseChatModel] = llm or self._build_model()
        self.structured_llm: Runnable = structured_llm or self._build_structured_llm()
        
        logger.info("ChatCommitDude initialized successfully")

    @staticmethod
    def build_messages(diff: str, system_prompt: str = SYSTEM_PROMPT) -> List[BaseMessage]:
        logger.debug(f"Building messages for diff (length: {len(diff)} chars)")
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Please create a commit for this Git diff my dude:\n{diff}"),
        ]
        logger.debug(f"Created {len(messages)} messages")
        return messages

    def _build_model(self) -> ChatOpenAI:
        logger.debug(f"Building ChatOpenAI model with name: {self.model}")
        llm = ChatOpenAI(model=self.model, temperature=0.2)
        logger.debug(f"Using LLM: {llm.model_name} with temperature: 0.2")
        return llm

    def _build_structured_llm(self) -> Runnable:
        logger.debug(f"Building structured LLM with output schema: {self.output.__name__}")
        structured_llm = self.llm.with_structured_output(self.output)
        logger.debug("Structured LLM configured successfully")
        return structured_llm

    def validate_num_tokens(self, diff: str) -> int:
        logger.debug("Validating token count for diff")
        num_tokens = self.llm.get_num_tokens(diff)
        logger.info(f"Diff token count: {num_tokens} (max allowed: {self.max_tokens})")
        
        if num_tokens > self.max_tokens:
            error_msg = f"Diff is too long. Max tokens: {self.max_tokens}, diff tokens: {num_tokens}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.debug("Token count validation passed")
        return num_tokens

    def _validate_api_key(self) -> None:
        logger.debug("Validating OPENAI_API_KEY")
        api_key = self.get_env("OPENAI_API_KEY")
        if not api_key:
            error_msg = "Missing OPENAI_API_KEY. Set it in your .env file."
            logger.error(error_msg)
            raise ValueError(error_msg)
        logger.debug("OPENAI_API_KEY found")

    def generate_commit_message(self, diff: str) -> CommitMessageResponse:
        logger.debug("Generating commit message from diff")
        messages = self.build_messages(diff)
        logger.info("Invoking LLM to generate commit message")
        
        try:
            result = self.structured_llm.invoke(messages)
            logger.info("Successfully generated commit message")
            logger.debug(f"Generated commit type: {getattr(result, 'type', 'unknown')}")
            return result
        except Exception as e:
            logger.error(f"Failed to generate commit message: {str(e)}", exc_info=True)
            raise

    def invoke(self, diff: str) -> CommitMessageResponse:
        logger.info("Starting commit message generation")
        logger.debug(f"Diff length: {len(diff)} characters")
        
        self.validate_num_tokens(diff)
        result = self.generate_commit_message(diff)
        
        logger.info("Commit message generation completed successfully")
        return result

test_instance = ChatCommitDude()