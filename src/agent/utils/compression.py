"""Context compression utilities."""

import json
import time
from pathlib import Path

from ..llm import create_response, extract_text


def estimate_tokens(messages: list) -> int:
    """Estimate token count from messages."""
    return len(json.dumps(messages, default=str)) // 4


def microcompact(messages: list):
    """Clear old tool results, keeping only last 3."""
    indices = []
    for i, msg in enumerate(messages):
        if msg["role"] == "user" and isinstance(msg.get("content"), list):
            for part in msg["content"]:
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    indices.append(part)
    if len(indices) <= 3:
        return
    for part in indices[:-3]:
        if isinstance(part.get("content"), str) and len(part["content"]) > 100:
            part["content"] = "[cleared]"


def auto_compact(messages: list, transcript_dir: Path) -> list:
    """Compress conversation and save transcript."""
    transcript_dir.mkdir(exist_ok=True)
    path = transcript_dir / f"transcript_{int(time.time())}.jsonl"
    with open(path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg, default=str) + "\n")
    conv_text = json.dumps(messages, default=str)[:80000]
    resp = create_response(
        [{"role": "user", "content": f"Summarize for continuity:\n{conv_text}"}],
        max_tokens=2000,
    )
    summary = extract_text(resp)
    return [
        {"role": "user", "content": f"[Compressed. Transcript: {path}]\n{summary}"},
        {"role": "assistant", "content": "Understood. Continuing with summary context."},
    ]
