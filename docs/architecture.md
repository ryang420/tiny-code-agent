# Project Architecture

## Overview

`tiny-code-agent` is an experimental autonomous coding agent focused on modularity, delegation, and long-running task support. The project combines a REPL-driven lead agent with persistent teammates, task tracking, message passing, context compression, and pluggable LLM providers.

The current implementation supports both Anthropic-style and OpenAI-style API formats through a shared adapter layer, so the rest of the agent can keep a single internal message and tool model.

## Features

- Multi-agent collaboration with spawnable teammate workers
- Persistent task management with dependency tracking
- In-memory todo tracking for short execution plans
- Background command execution with notification draining
- Context compression and transcript persistence for long sessions
- Skill loading from local `skills/` definitions
- Message bus for teammate coordination
- Subagent delegation for isolated exploration or execution
- Provider-agnostic LLM integration for Anthropic and OpenAI-compatible APIs
- REPL interface for interactive agent use

## High-Level Architecture

The system is organized around a lead agent loop that talks to an LLM, exposes tools, and coordinates auxiliary systems.

```text
User -> REPL (src/main.py)
     -> Lead Agent Loop (src/agent/agent.py)
     -> LLM Adapter (src/agent/llm.py)
     -> Tools / Managers / Utilities
```

## Layered Architecture View

The current codebase is modular, but the earlier version of this document mostly described modules by directory. A more complete architecture view should also describe the system by responsibility layers.

The target layered view is:

```text
CLI / UI Layer
    ->
Session State Layer
    ->
Main Orchestration Layer <-> Task / Multi-Agent Layer
    ->
Tool Protocol Layer
Context Assembly Layer
Permission and Approval Layer
Prompt and Mode Assembly Layer
Extension Layer: MCP / LSP / Plugins
    ->
File / Shell / Search Tools
```

### Layer Mapping

### CLI / UI Layer

This layer is currently implemented by `src/main.py`.

Current responsibilities:

- Read user input from the terminal
- Dispatch the prompt into the lead agent loop
- Render the final assistant output
- Expose a few REPL commands such as `/compact`, `/tasks`, `/team`, and `/inbox`

Current gap:

- The system only has a CLI entry point and does not yet have a dedicated UI abstraction, API server, or transport-independent presentation layer.

### Session State Layer

This layer is only partially implemented.

Current responsibilities are spread across:

- Conversation history in the REPL process
- Persistent task files in `.tasks/`
- Team configuration and inboxes in `.team/`
- Transcript snapshots in `.transcripts/`

Current gap:

- There is no explicit session state component that owns conversation lifecycle, session identity, checkpoints, resumability, or multi-session isolation.
- State is stored in several places, but not unified behind a single session model.

### Main Orchestration Layer

This layer is mainly implemented by `src/agent/agent.py`.

Current responsibilities:

- Build the system prompt
- Register tools and dispatch handlers
- Coordinate LLM calls
- Process tool loops
- Merge background notifications and inbox messages into the active turn

This is the core control plane for the lead agent.

### Task / Multi-Agent Layer

This layer is implemented by:

- `src/agent/managers/task_manager.py`
- `src/agent/managers/teammate_manager.py`
- `src/agent/managers/message_bus.py`
- `src/agent/core/subagent.py`

Current responsibilities:

- Persistent task creation and claiming
- Teammate spawning and idle/work transitions
- Subagent execution
- Inter-agent messaging

Current gap:

- Coordination logic exists, but it is still tightly coupled to local threads and filesystem state.
- Multi-agent scheduling, supervision, and recovery are still basic.

### Tool Protocol Layer

This layer exists, but is still implicit rather than first-class.

Current implementation is spread across:

- `TOOLS` and `TOOL_HANDLERS` in `src/agent/agent.py`
- Provider translation logic in `src/agent/llm.py`
- Tool execution primitives in `src/agent/core/base_tools.py`

Current responsibilities:

- Define tool schemas
- Translate tool calls between internal format and provider-specific APIs
- Return tool results back into the agent loop

Current gap:

- There is no standalone internal tool protocol module with typed request and response models.
- Tool lifecycle, validation, auditing, and policy enforcement are not yet separated cleanly from orchestration.

### Context Assembly Layer

This layer is partially implemented.

Current implementation is mainly in:

- `src/agent/agent.py`
- `src/agent/utils/compression.py`

Current responsibilities:

- Maintain message history
- Compact older tool results
- Summarize oversized conversations
- Inject background results and inbox content into the prompt context

Current gap:

- Context assembly is currently embedded inside the main loop instead of being isolated as an explicit pipeline.
- There is no strategy layer for retrieval, ranking, memory selection, or context budgeting by source type.

### Permission and Approval Layer

This layer is present only in a very limited form.

Current implementation is mainly in:

- `src/agent/core/base_tools.py`
- Coordination helpers in `src/agent/utils/protocols.py`

Current responsibilities:

- Block a few obviously dangerous shell commands
- Support basic plan/shutdown coordination messages

Current gap:

- There is no unified permission model for read, write, shell, network, background, or delegation actions.
- Approval is not yet a first-class policy engine.
- Risk classification and operator approval workflows are still missing.

### Prompt and Mode Assembly Layer

This layer is also only partially implemented.

Current implementation is mainly in:

- `SYSTEM` prompt construction in `src/agent/agent.py`
- `src/agent/managers/skill_loader.py`
- Provider adaptation in `src/agent/llm.py`

Current responsibilities:

- Build the lead-agent system prompt
- Inject skill descriptions
- Select the active LLM provider

Current gap:

- Prompt composition is still mostly string-based and centralized.
- There is no formal mode system for planning mode, execution mode, review mode, safe mode, or provider-specific prompt profiles.

### Extension Layer: MCP / LSP / Plugins

This layer is mostly absent in the current implementation.

Current implementation status:

- The skill system exists and provides a lightweight extension mechanism through local `skills/`.

Current gap:

- There is no MCP integration layer.
- There is no LSP-backed code intelligence layer.
- There is no plugin runtime, plugin contract, or extension lifecycle management.

### File / Shell / Search Tool Layer

This layer is partially implemented.

Current implementation is mainly in:

- `src/agent/core/base_tools.py`
- `src/agent/managers/background_manager.py`

Current responsibilities:

- File read, write, and edit
- Shell command execution
- Background command execution

Current gap:

- Search is not yet a first-class tool category.
- Tooling breadth is still narrow compared with the layered target architecture.
- Safety, observability, and tool specialization still need work.

### Runtime Flow

1. The user enters a prompt in the REPL.
2. The prompt is appended to conversation history.
3. The lead agent runs pre-processing steps such as compression checks, background result draining, and inbox polling.
4. The LLM adapter sends the request to the configured provider.
5. If the model returns tool calls, the agent dispatches them to local handlers.
6. Tool results are appended back into history and the loop continues until the model returns a final answer.
7. The final assistant text is printed to the terminal.

## Code Structure

```text
src/
├── main.py
└── agent/
    ├── agent.py
    ├── llm.py
    ├── core/
    │   ├── base_tools.py
    │   └── subagent.py
    ├── managers/
    │   ├── background_manager.py
    │   ├── message_bus.py
    │   ├── skill_loader.py
    │   ├── task_manager.py
    │   ├── teammate_manager.py
    │   └── todo_manager.py
    └── utils/
        ├── compression.py
        └── protocols.py
```

## Core Modules

### `src/main.py`

Provides the command-line REPL. It loads environment variables, accepts user input, forwards prompts to the agent loop, and prints assistant responses.

### `src/agent/agent.py`

Acts as the central orchestrator. It defines:

- The system prompt
- The tool registry and dispatch handlers
- The main execution loop
- Integration points for managers, compression, and messaging

This file is the heart of the lead agent runtime.

### `src/agent/llm.py`

Normalizes LLM access behind a provider-agnostic interface. It is responsible for:

- Selecting Anthropic or OpenAI mode from environment variables
- Converting internal message history into provider-specific request formats
- Translating provider responses back into a normalized internal block structure
- Preserving tool call semantics across providers

### `src/agent/core/base_tools.py`

Implements local execution primitives such as shell commands and file operations. These are exposed to the model as callable tools.

### `src/agent/core/subagent.py`

Runs an isolated agent loop for delegated exploration or work. This gives the lead agent a bounded execution surface for subtasks.

## Manager Layer

### `background_manager.py`

Runs long-lived shell commands in background threads and stores results until the main loop consumes them.

### `message_bus.py`

Implements teammate communication through JSONL inbox files under `.team/inbox/`.

### `skill_loader.py`

Loads project-specific skills from the `skills/` directory, allowing the agent to reference specialized instructions.

### `task_manager.py`

Stores persistent tasks as JSON files under `.tasks/`, including state, ownership, and dependencies.

### `teammate_manager.py`

Spawns and supervises persistent teammate agents. Teammates can receive messages, claim tasks, idle, and resume when new work appears.

### `todo_manager.py`

Tracks short-lived execution checklists in memory for the lead agent.

## Utility Layer

### `compression.py`

Handles transcript compaction. It clears older bulky tool results, saves full transcripts to `.transcripts/`, and asks the active model to summarize prior context when the history grows too large.

### `protocols.py`

Provides coordination helpers such as shutdown requests and plan approval responses between agents.

## State and Persistence

The project uses lightweight filesystem-based persistence instead of a database.

- `.tasks/`: task records
- `.team/`: team configuration and inbox storage
- `.transcripts/`: archived conversation snapshots
- `skills/`: local skill definitions

This approach keeps the system easy to inspect, debug, and extend.

## Technologies

### Language and Runtime

- Python 3

### Libraries

- `python-dotenv` for environment loading
- `anthropic` for Anthropic-compatible APIs
- `openai` for OpenAI-compatible APIs
- `pytest` for testing

### Communication and Storage Patterns

- JSON and JSONL for message passing and persistence
- Local filesystem directories for state management
- Threads for background jobs and teammate execution

## Design Characteristics

- Modular: responsibilities are separated into core, manager, utility, and adapter layers
- Local-first: persistent state is stored in project files instead of external services
- Extensible: tools, managers, and providers can be expanded incrementally
- Agent-oriented: the architecture is built around tool-using LLM loops rather than single-shot prompts
- Experimental: the system favors inspectability and iteration speed over production hardening

## Architectural Gaps

Compared with a fuller agent platform architecture, the most important missing or weakly-defined layers are:

- An explicit session state layer
- A first-class context assembly pipeline
- A unified permission and approval layer
- A dedicated prompt and mode assembly layer
- A formalized tool protocol abstraction
- A real extension layer for MCP, LSP, and plugins

In other words, the current project already has many of the raw ingredients, but several of them are still embedded inside `agent.py` or scattered across managers rather than promoted into independent architectural layers.

## Extending the System

Common extension points include:

- Adding new tools in `src/agent/agent.py`
- Introducing new managers under `src/agent/managers/`
- Expanding provider support in `src/agent/llm.py`
- Adding skills under `skills/`
- Improving safety, persistence, and testing around command execution

## Related Documents

- [Production Readiness Roadmap](./production-readiness.md)
