"""Provider-agnostic LLM adapter for Anthropic and OpenAI-style APIs."""

import json
import os
from dataclasses import dataclass
from typing import Any

MODEL = os.environ["MODEL_ID"]


@dataclass
class LLMResponse:
    """Normalized response shape used across the agent."""

    content: list[dict[str, Any]]
    stop_reason: str

    @property
    def text(self) -> str:
        """Concatenate text blocks from the response."""
        return "".join(block.get("text", "") for block in self.content if block.get("type") == "text")


def _provider() -> str:
    """Select provider based on configured credentials."""
    explicit = os.getenv("LLM_PROVIDER")
    if explicit:
        return explicit.lower()
    if os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_BASE_URL"):
        return "openai"
    return "anthropic"


def _make_client():
    """Create the underlying SDK client for the active provider."""
    provider = _provider()
    if provider == "openai":
        from openai import OpenAI

        return OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )
    from anthropic import Anthropic

    return Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))


CLIENT = _make_client()


def create_response(messages: list, max_tokens: int = 8000, system: str | None = None, tools: list | None = None) -> LLMResponse:
    """Create a model response using the configured provider."""
    if _provider() == "openai":
        return _create_openai_response(messages, max_tokens, system, tools or [])
    return _create_anthropic_response(messages, max_tokens, system, tools or [])


def assistant_message_content(response: LLMResponse):
    """Return a serializable assistant content payload for transcript history."""
    return response.content


def extract_text(response: LLMResponse) -> str:
    """Extract text output from a normalized response."""
    return response.text


def _create_anthropic_response(messages: list, max_tokens: int, system: str | None, tools: list) -> LLMResponse:
    """Call Anthropic using the agent's internal message format."""
    kwargs = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools
    response = CLIENT.messages.create(**kwargs)
    blocks = []
    for block in response.content:
        if block.type == "text":
            blocks.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            blocks.append(
                {
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                }
            )
    return LLMResponse(content=blocks, stop_reason=response.stop_reason or "end_turn")


def _create_openai_response(messages: list, max_tokens: int, system: str | None, tools: list) -> LLMResponse:
    """Call OpenAI chat completions after translating internal history."""
    chat_messages = _to_openai_messages(messages, system)
    kwargs = {
        "model": MODEL,
        "messages": chat_messages,
        "max_tokens": max_tokens,
    }
    if tools:
        kwargs["tools"] = [_anthropic_tool_to_openai(tool) for tool in tools]
    response = CLIENT.chat.completions.create(**kwargs)
    choice = response.choices[0].message
    blocks = []
    if choice.content:
        blocks.append({"type": "text", "text": choice.content})
    for tool_call in choice.tool_calls or []:
        arguments = tool_call.function.arguments or "{}"
        try:
            parsed_arguments = json.loads(arguments)
        except json.JSONDecodeError:
            parsed_arguments = {"raw_arguments": arguments}
        blocks.append(
            {
                "type": "tool_use",
                "id": tool_call.id,
                "name": tool_call.function.name,
                "input": parsed_arguments,
            }
        )
    stop_reason = "tool_use" if choice.tool_calls else (response.choices[0].finish_reason or "end_turn")
    return LLMResponse(content=blocks, stop_reason=stop_reason)


def _anthropic_tool_to_openai(tool: dict) -> dict:
    """Convert Anthropic tool schema to OpenAI function tool schema."""
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }


def _to_openai_messages(messages: list, system: str | None) -> list[dict[str, Any]]:
    """Translate internal message history to OpenAI chat messages."""
    converted = []
    if system:
        converted.append({"role": "system", "content": system})
    for msg in messages:
        role = msg["role"]
        content = msg.get("content")
        if isinstance(content, str):
            converted.append({"role": role, "content": content})
            continue
        if role == "assistant":
            converted.append(_assistant_blocks_to_openai_message(content))
            continue
        if role == "user":
            converted.extend(_user_blocks_to_openai_messages(content))
            continue
        converted.append({"role": role, "content": json.dumps(content, ensure_ascii=False)})
    return converted


def _assistant_blocks_to_openai_message(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert normalized assistant blocks into one OpenAI assistant message."""
    text_parts = []
    tool_calls = []
    for block in blocks:
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))
        elif block.get("type") == "tool_use":
            tool_calls.append(
                {
                    "id": block["id"],
                    "type": "function",
                    "function": {
                        "name": block["name"],
                        "arguments": json.dumps(block.get("input", {}), ensure_ascii=False),
                    },
                }
            )
    message = {"role": "assistant", "content": "".join(text_parts) or None}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return message


def _user_blocks_to_openai_messages(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert user-side structured content to OpenAI chat messages."""
    converted = []
    text_parts = []
    for block in blocks:
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))
        elif block.get("type") == "tool_result":
            if text_parts:
                converted.append({"role": "user", "content": "".join(text_parts)})
                text_parts = []
            converted.append(
                {
                    "role": "tool",
                    "tool_call_id": block["tool_use_id"],
                    "content": str(block.get("content", "")),
                }
            )
    if text_parts:
        converted.append({"role": "user", "content": "".join(text_parts)})
    return converted
