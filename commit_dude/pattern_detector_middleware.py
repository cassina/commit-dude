import re
import yaml
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from langchain.agents.middleware import AgentMiddleware  # as per docs


class SecretPatternDetectorMiddleware(AgentMiddleware):
    def __init__(
        self,
        patterns_yaml_path: Union[str, Path],
        confidence_threshold: float = 0.5,
        strategy: str = "block",
    ):
        """
        patterns_yaml_path: path to YAML containing regex patterns with id & (optional) confidence
        confidence_threshold: only apply patterns whose confidence >= threshold
        strategy: what to do when a match is found: "block" (raise error) or "redact"/"mask"
        """
        self.strategy = strategy
        self.patterns = self._load_patterns(patterns_yaml_path)
        self.compiled: List[Tuple[str, re.Pattern]] = self._compile_patterns(
            self.patterns, confidence_threshold
        )

    def _load_patterns(self, yaml_path: Union[str, Path]) -> List[Dict[str, Any]]:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("patterns", [])

    def _compile_patterns(
        self, entries: List[Dict[str, Any]], threshold: float
    ) -> List[Tuple[str, re.Pattern]]:
        compiled: List[Tuple[str, re.Pattern]] = []
        for e in entries:
            pid = e.get("id", "<unknown>")
            pat = e.get("pattern")
            confidence = e.get("confidence", 0.0)
            if pat and confidence >= threshold:
                try:
                    regex = re.compile(pat)
                    compiled.append((pid, regex))
                except re.error as err:
                    # You may want logging instead of print in production
                    print(f"WARNING: invalid regex for id={pid}: {err}")
        return compiled

    def before_model(self, request: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        text = ""

        # Case 1: simple string input
        if "input" in request and isinstance(request["input"], str):
            text = request["input"]

        # Case 2: list of LangChain messages (HumanMessage, AIMessage)
        elif "messages" in request and isinstance(request["messages"], list):
            text = " ".join([getattr(m, "content", "") for m in request["messages"]])

        matches: List[Tuple[str, str]] = []
        for pid, regex in self.compiled:
            for m in regex.finditer(text):
                matches.append((pid, m.group(0)))

        if matches:
            if self.strategy == "block":
                raise RuntimeError(f"Secret pattern(s) detected: {matches}")

            elif self.strategy in ("redact", "mask"):
                replacement = (
                    "[REDACTED_SECRET]" if self.strategy == "redact" else "[MASKED]"
                )

                new_text = text
                for _, matched in matches:
                    new_text = new_text.replace(matched, replacement)

                # rewrite input
                if "input" in request:
                    request["input"] = new_text

                # rewrite messages
                if "messages" in request:
                    new_messages = []
                    for msg in request["messages"]:
                        content = getattr(msg, "content", "")
                        for _, matched in matches:
                            content = content.replace(matched, replacement)

                        # messages are objects → clone them properly
                        msg_copy = msg.copy(update={"content": content})
                        new_messages.append(msg_copy)

                    request["messages"] = new_messages

                return request

            else:
                raise RuntimeError(f"Unknown strategy '{self.strategy}'")

        return request

    def after_model(self, response: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        # If you also want to inspect model’s output, implement this.
        return response

    def modify_model_request(self, request: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        # If you want to change the tools, messages, etc right before model call.
        return request
