"""Subagent spawning for isolated exploration and work."""

from .base_tools import run_bash, run_read, run_write, run_edit
from ..llm import assistant_message_content, create_response, extract_text


def run_subagent(prompt: str, agent_type: str = "Explore") -> str:
    """Spawn isolated subagent for exploration or work."""
    sub_tools = [
        {
            "name": "bash",
            "description": "Run command.",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
        {
            "name": "read_file",
            "description": "Read file.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    ]
    if agent_type != "Explore":
        sub_tools += [
            {
                "name": "write_file",
                "description": "Write file.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "edit_file",
                "description": "Edit file.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "old_text": {"type": "string"},
                        "new_text": {"type": "string"},
                    },
                    "required": ["path", "old_text", "new_text"],
                },
            },
        ]
    sub_handlers = {
        "bash": lambda **kw: run_bash(kw["command"]),
        "read_file": lambda **kw: run_read(kw["path"]),
        "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
        "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    }
    sub_msgs = [{"role": "user", "content": prompt}]
    resp = None
    for _ in range(30):
        resp = create_response(sub_msgs, max_tokens=8000, tools=sub_tools)
        sub_msgs.append({"role": "assistant", "content": assistant_message_content(resp)})
        if resp.stop_reason != "tool_use":
            break
        results = []
        for b in resp.content:
            if b["type"] == "tool_use":
                h = sub_handlers.get(b["name"], lambda **kw: "Unknown tool")
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": b["id"],
                        "content": str(h(**b["input"]))[:50000],
                    }
                )
        sub_msgs.append({"role": "user", "content": results})
    if resp:
        return extract_text(resp) or "(no summary)"
    return "(subagent failed)"
