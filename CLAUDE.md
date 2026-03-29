# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an experimental code agent implementation that demonstrates a full-featured autonomous agent system with multi-agent collaboration, task management, and context compression capabilities.

## Architecture

The codebase is now organized into a modular structure:

```
src/
├── agent/
│   ├── __init__.py           # Package initialization
│   ├── agent.py              # Main agent loop and tool dispatch
│   ├── core/                 # Core functionality
│   │   ├── __init__.py
│   │   ├── base_tools.py     # File operations and bash execution
│   │   └── subagent.py       # Subagent spawning
│   ├── managers/             # Manager classes
│   │   ├── __init__.py
│   │   ├── background_manager.py  # Background task execution
│   │   ├── message_bus.py         # Inter-agent messaging
│   │   ├── skill_loader.py        # Skill system
│   │   ├── task_manager.py        # Persistent task management
│   │   ├── teammate_manager.py    # Multi-agent coordination
│   │   └── todo_manager.py        # In-memory todo tracking
│   └── utils/                # Utility functions
│       ├── __init__.py
│       ├── compression.py    # Context compression
│       └── protocols.py      # Shutdown and plan approval
├── main.py                   # REPL entry point
```

### Core Systems

1. **Base Tools** (`core/base_tools.py`): File operations (read/write/edit) and bash execution with safety checks
2. **Subagent System** (`core/subagent.py`): Spawns isolated agent instances for exploration or delegation
3. **Todo Management** (`managers/todo_manager.py`): In-memory checklist tracking with status validation
4. **Task Management** (`managers/task_manager.py`): Persistent file-based tasks in `.tasks/` with dependencies and ownership
5. **Background Execution** (`managers/background_manager.py`): Threaded command execution with notification queue
6. **Messaging Bus** (`managers/message_bus.py`): JSONL-based inbox system in `.team/inbox/` for inter-agent communication
7. **Teammate System** (`managers/teammate_manager.py`): Spawns autonomous agents that work/idle/auto-claim tasks
8. **Skills System** (`managers/skill_loader.py`): Loads specialized knowledge from `skills/` directory (SKILL.md files with frontmatter)
9. **Context Compression** (`utils/compression.py`): Auto-compacts at 100k tokens, saves transcripts to `.transcripts/`
10. **Protocols** (`utils/protocols.py`): Shutdown and plan approval mechanisms

### Agent Loop Flow

Before each LLM call:
- Microcompact: Clear old tool results (keep last 3)
- Auto-compact: If >100k tokens, compress conversation and save transcript
- Drain background notifications
- Check inbox for messages

### Key Directories

- `.tasks/` - Persistent task files (task_N.json)
- `.team/` - Team configuration and inbox files
- `.transcripts/` - Compressed conversation history
- `skills/` - Skill definitions (SKILL.md with frontmatter)

## Running the Agent

```bash
# Setup environment
cp .env.example .env
# Edit .env to add your ANTHROPIC_API_KEY and MODEL_ID

# Install dependencies
pip install -r requirements.txt

# Run the agent (new modular version)
python src/main.py

```

## REPL Commands

- `/compact` - Manually trigger context compression
- `/tasks` - List all tasks
- `/team` - List all teammates and their status
- `/inbox` - Check lead agent's inbox
- `q`, `exit`, or Ctrl+C - Exit

## Configuration

Required environment variables:
- `ANTHROPIC_API_KEY` - Your API key
- `MODEL_ID` - Model to use (e.g., claude-sonnet-4-6)

Optional:
- `ANTHROPIC_BASE_URL` - For Anthropic-compatible providers (MiniMax, GLM, Kimi, DeepSeek)

See `.env.example` for provider-specific configurations and benchmark scores.

## Development

### Adding New Tools

1. Add tool handler to `TOOL_HANDLERS` dict in `agent/agent.py`
2. Add tool definition to `TOOLS` list in `agent/agent.py`
3. Implement the handler function in appropriate module

### Adding New Managers

1. Create new manager class in `agent/managers/`
2. Import and initialize in `agent/agent.py`
3. Add to `agent/managers/__init__.py`

### Testing

Run tests with:
```bash
pytest
```

## Safety Features

- Path validation: All file operations restricted to workspace
- Command blocking: Dangerous commands (rm -rf /, sudo, etc.) are blocked
- Timeouts: Commands timeout after 120s by default
- Output truncation: Results limited to 50k characters

