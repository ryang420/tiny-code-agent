#!/usr/bin/env python3
"""REPL interface for the agent."""

import json
import os
from dotenv import load_dotenv

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

from agent.agent import agent_loop, TASK_MGR, TEAM, BUS


def main():
    """Run the agent REPL."""
    history = []
    while True:
        try:
            query = input("\033[36ms_full >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        if query.strip() == "/compact":
            if history:
                from agent.utils import auto_compact
                from agent.agent import TRANSCRIPT_DIR
                print("[manual compact via /compact]")
                history[:] = auto_compact(history, TRANSCRIPT_DIR)
            continue
        if query.strip() == "/tasks":
            print(TASK_MGR.list_all())
            continue
        if query.strip() == "/team":
            print(TEAM.list_all())
            continue
        if query.strip() == "/inbox":
            print(json.dumps(BUS.read_inbox("lead"), indent=2))
            continue
        history.append({"role": "user", "content": query})
        agent_loop(history)
        print()


if __name__ == "__main__":
    main()
