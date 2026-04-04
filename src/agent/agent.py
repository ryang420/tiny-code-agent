#!/usr/bin/env python3
"""Main agent loop and tool dispatch."""

import json
import os
from pathlib import Path

from .core import run_bash, run_read, run_write, run_edit, run_subagent
from .llm import assistant_message_content, create_response
from .managers import (
    BackgroundManager,
    MessageBus,
    SkillLoader,
    TaskManager,
    TeammateManager,
    TodoManager,
)
from .utils import (
    estimate_tokens,
    microcompact,
    auto_compact,
    handle_shutdown_request,
    handle_plan_review,
)
MODEL = os.environ["MODEL_ID"]

WORKDIR = Path.cwd()
TEAM_DIR = WORKDIR / ".team"
INBOX_DIR = TEAM_DIR / "inbox"
TASKS_DIR = WORKDIR / ".tasks"
SKILLS_DIR = WORKDIR / "skills"
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
TOKEN_THRESHOLD = 100000

VALID_MSG_TYPES = {
    "message",
    "broadcast",
    "shutdown_request",
    "shutdown_response",
    "plan_approval_response",
}

# Initialize global instances
TODO = TodoManager()
SKILLS = SkillLoader(SKILLS_DIR)
TASK_MGR = TaskManager(TASKS_DIR)
BG = BackgroundManager(WORKDIR)
BUS = MessageBus(INBOX_DIR)
TEAM = TeammateManager(TEAM_DIR, WORKDIR, BUS, TASK_MGR)

# System prompt
SYSTEM = f"""You are a coding agent at {WORKDIR}. Use tools to solve tasks.
Prefer task_create/task_update/task_list for multi-step work. Use TodoWrite for short checklists.
Use task for subagent delegation. Use load_skill for specialized knowledge.
Skills: {SKILLS.descriptions()}"""

# Tool handlers
TOOL_HANDLERS = {
    "bash": lambda **kw: run_bash(kw["command"]),
    "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "TodoWrite": lambda **kw: TODO.update(kw["items"]),
    "task": lambda **kw: run_subagent(kw["prompt"], kw.get("agent_type", "Explore")),
    "load_skill": lambda **kw: SKILLS.load(kw["name"]),
    "compress": lambda **kw: "Compressing...",
    "background_run": lambda **kw: BG.run(kw["command"], kw.get("timeout", 120)),
    "check_background": lambda **kw: BG.check(kw.get("task_id")),
    "task_create": lambda **kw: TASK_MGR.create(
        kw["subject"], kw.get("description", "")
    ),
    "task_get": lambda **kw: TASK_MGR.get(kw["task_id"]),
    "task_update": lambda **kw: TASK_MGR.update(
        kw["task_id"],
        kw.get("status"),
        kw.get("add_blocked_by"),
        kw.get("add_blocks"),
    ),
    "task_list": lambda **kw: TASK_MGR.list_all(),
    "spawn_teammate": lambda **kw: TEAM.spawn(kw["name"], kw["role"], kw["prompt"]),
    "list_teammates": lambda **kw: TEAM.list_all(),
    "send_message": lambda **kw: BUS.send(
        "lead", kw["to"], kw["content"], kw.get("msg_type", "message")
    ),
    "read_inbox": lambda **kw: json.dumps(BUS.read_inbox("lead"), indent=2),
    "broadcast": lambda **kw: BUS.broadcast("lead", kw["content"], TEAM.member_names()),
    "shutdown_request": lambda **kw: handle_shutdown_request(kw["teammate"], BUS),
    "plan_approval": lambda **kw: handle_plan_review(
        kw["request_id"], kw["approve"], BUS, kw.get("feedback", "")
    ),
    "idle": lambda **kw: "Lead does not idle.",
    "claim_task": lambda **kw: TASK_MGR.claim(kw["task_id"], "lead"),
}

# Tool definitions
TOOLS = [
    {
        "name": "bash",
        "description": "Run a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read file contents.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace exact text in file.",
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
    {
        "name": "TodoWrite",
        "description": "Update task tracking list.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"],
                            },
                            "activeForm": {"type": "string"},
                        },
                        "required": ["content", "status", "activeForm"],
                    },
                }
            },
            "required": ["items"],
        },
    },
    {
        "name": "task",
        "description": "Spawn a subagent for isolated exploration or work.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "agent_type": {
                    "type": "string",
                    "enum": ["Explore", "general-purpose"],
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "load_skill",
        "description": "Load specialized knowledge by name.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "compress",
        "description": "Manually compress conversation context.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "background_run",
        "description": "Run command in background thread.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout": {"type": "integer"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "check_background",
        "description": "Check background task status.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
        },
    },
    {
        "name": "task_create",
        "description": "Create a persistent file task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["subject"],
        },
    },
    {
        "name": "task_get",
        "description": "Get task details by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "task_update",
        "description": "Update task status or dependencies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "deleted"],
                },
                "add_blocked_by": {"type": "array", "items": {"type": "integer"}},
                "add_blocks": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "task_list",
        "description": "List all tasks.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "spawn_teammate",
        "description": "Spawn a persistent autonomous teammate.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "role": {"type": "string"},
                "prompt": {"type": "string"},
            },
            "required": ["name", "role", "prompt"],
        },
    },
    {
        "name": "list_teammates",
        "description": "List all teammates.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "send_message",
        "description": "Send a message to a teammate.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "content": {"type": "string"},
                "msg_type": {"type": "string", "enum": list(VALID_MSG_TYPES)},
            },
            "required": ["to", "content"],
        },
    },
    {
        "name": "read_inbox",
        "description": "Read and drain the lead's inbox.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "broadcast",
        "description": "Send message to all teammates.",
        "input_schema": {
            "type": "object",
            "properties": {"content": {"type": "string"}},
            "required": ["content"],
        },
    },
    {
        "name": "shutdown_request",
        "description": "Request a teammate to shut down.",
        "input_schema": {
            "type": "object",
            "properties": {"teammate": {"type": "string"}},
            "required": ["teammate"],
        },
    },
    {
        "name": "plan_approval",
        "description": "Approve or reject a teammate's plan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "request_id": {"type": "string"},
                "approve": {"type": "boolean"},
                "feedback": {"type": "string"},
            },
            "required": ["request_id", "approve"],
        },
    },
    {
        "name": "idle",
        "description": "Enter idle state.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "claim_task",
        "description": "Claim a task from the board.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
]


def agent_loop(messages: list):
    """Main agent loop with compression and tool execution."""
    rounds_without_todo = 0
    while True:
        # Compression pipeline
        microcompact(messages)
        if estimate_tokens(messages) > TOKEN_THRESHOLD:
            print("[auto-compact triggered]")
            messages[:] = auto_compact(messages, TRANSCRIPT_DIR)
        # Drain background notifications
        notifs = BG.drain()
        if notifs:
            txt = "\n".join(
                f"[bg:{n['task_id']}] {n['status']}: {n['result']}" for n in notifs
            )
            messages.append(
                {"role": "user", "content": f"<background-results>\n{txt}\n</background-results>"}
            )
            messages.append(
                {"role": "assistant", "content": "Noted background results."}
            )
        # Check lead inbox
        inbox = BUS.read_inbox("lead")
        if inbox:
            messages.append(
                {"role": "user", "content": f"<inbox>{json.dumps(inbox, indent=2)}</inbox>"}
            )
            messages.append({"role": "assistant", "content": "Noted inbox messages."})
        # LLM call
        response = create_response(messages, max_tokens=8000, system=SYSTEM, tools=TOOLS)
        messages.append({"role": "assistant", "content": assistant_message_content(response)})
        if response.stop_reason != "tool_use":
            return
        # Tool execution
        results = []
        used_todo = False
        manual_compress = False
        for block in response.content:
            if block["type"] == "tool_use":
                if block["name"] == "compress":
                    manual_compress = True
                handler = TOOL_HANDLERS.get(block["name"])
                try:
                    output = (
                        handler(**block["input"])
                        if handler
                        else f"Unknown tool: {block['name']}"
                    )
                except Exception as e:
                    output = f"Error: {e}"
                print(f"> {block['name']}: {str(output)[:200]}")
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": str(output),
                    }
                )
                if block["name"] == "TodoWrite":
                    used_todo = True
        # Todo nag reminder
        rounds_without_todo = 0 if used_todo else rounds_without_todo + 1
        if TODO.has_open_items() and rounds_without_todo >= 3:
            results.insert(
                0, {"type": "text", "text": "<reminder>Update your todos.</reminder>"}
            )
        messages.append({"role": "user", "content": results})
        # Manual compress
        if manual_compress:
            print("[manual compact]")
            messages[:] = auto_compact(messages, TRANSCRIPT_DIR)
