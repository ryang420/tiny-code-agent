# Production Readiness Roadmap

## Overview

`tiny-code-agent` is already a strong experimental foundation, but it still needs several enhancements before it can be considered production ready.

The current gaps are concentrated in five areas:

- Reliability
- Security
- Data integrity
- Observability
- Deployment and operational maturity

This document summarizes the recommended enhancements and groups them by priority.

## P0: Must-Have Before Production

### Reliability and Failure Handling

- Add consistent exception handling across the full request lifecycle.
- Surface provider and tool errors clearly to the user instead of failing silently.
- Implement retry, timeout, and exponential backoff for LLM provider calls.
- Add fallback behavior for transient provider outages and rate limits.
- Define recovery behavior after process restarts, including which state is durable and which can be rebuilt.

### Command Execution Safety

- Replace or tightly constrain `shell=True` command execution.
- Introduce a more robust allowlist and denylist model for shell commands.
- Separate permissions for reading files, writing files, running commands, networking, and background jobs.
- Add approval gates for high-risk actions.

### Secret and Data Protection

- Redact API keys, tokens, and sensitive environment variables from logs, transcripts, and inbox messages.
- Prevent accidental persistence of secrets into `.transcripts/`, `.tasks/`, or `.team/`.
- Add secure configuration validation at startup.

### Consistency and Concurrency Control

- Add file locking or atomic write strategies for task files and inbox files.
- Prevent race conditions when multiple teammates claim tasks or read/write message queues.
- Add schema validation for persisted task and message records.
- Make message handling and task updates idempotent to avoid duplicate processing.

## P1: Strongly Recommended for Operational Use

### Observability

- Introduce structured logging with stable fields such as request ID, session ID, task ID, teammate name, tool name, provider, latency, and outcome.
- Record model usage data such as token counts, tool-call counts, and provider error rates.
- Add metrics for response success rate, command failures, background task failures, and queue depth.
- Add tracing or correlation IDs across lead agent, teammate agents, and background tasks.

### Testing and Quality Assurance

- Build unit tests for tool execution, message translation, task persistence, and compression behavior.
- Add integration tests for Anthropic and OpenAI-compatible execution flows.
- Add regression tests for tool-call loops and multi-step agent interactions.
- Add concurrency tests for background execution, message bus handling, and task claiming.
- Add fault-injection tests for provider timeouts, malformed responses, and partial filesystem failures.

### Runtime and Process Management

- Add health checks and readiness checks.
- Support graceful shutdown for the lead agent, teammates, and background workers.
- Add startup validation for required environment variables and provider configuration.
- Define retention and cleanup policies for transcripts, background results, and task history.

## P2: Important for Scale and Maintainability

### Architecture Evolution

- Abstract persistence behind interfaces so storage can move from filesystem JSON to SQLite, PostgreSQL, or Redis.
- Replace ad hoc dict-based protocol payloads with typed internal models.
- Separate orchestration logic from transport and persistence layers more explicitly.
- Add versioning for persisted schemas and message contracts.
- Promote implicit responsibilities into explicit architectural layers, especially session state, context assembly, permission and approval, prompt and mode assembly, and tool protocol handling.
- Introduce a real extension layer for MCP, LSP, and plugin-based integrations.

### Multi-User and Multi-Workspace Support

- Add session isolation so different users or workspaces do not share state accidentally.
- Define tenant-aware task, transcript, and message storage.
- Add authentication and authorization if the system is exposed beyond local single-user usage.

### Human-in-the-Loop Control

- Add approval workflows for file writes, shell commands, and task execution in restricted environments.
- Allow operator review for plan generation, teammate spawning, and background jobs.
- Support policy-based execution modes such as local-dev, sandboxed, and production-locked.

## Suggested Delivery Sequence

The most practical order for implementation is:

1. Secure command execution and secret handling.
2. Add provider reliability features such as retry, timeout, and error reporting.
3. Fix persistence consistency with atomic writes, locking, and schema validation.
4. Add structured logging, metrics, and traceability.
5. Expand automated testing and introduce deployment/runtime controls.
6. Evolve storage and orchestration architecture for scale.

## Recommended Concrete Enhancements by Module

### `src/agent/llm.py`

- Add provider-specific retry and timeout policies.
- Normalize provider errors into a shared internal error model.
- Record token usage and latency metadata.
- Add circuit-breaker or fallback behavior for repeated failures.

### `src/agent/agent.py`

- Centralize top-level error handling and user-visible error reporting.
- Add correlation IDs for each prompt/response/tool cycle.
- Separate orchestration from presentation logic more cleanly.

### `src/agent/core/base_tools.py`

- Remove broad shell execution where possible.
- Add command policy enforcement and stronger sandboxing controls.
- Improve file operation validation and audit logging.

### `src/agent/managers/background_manager.py`

- Add cancellation support, better status modeling, and persistence of running task metadata.
- Introduce safer command execution controls.
- Record execution duration, exit code, and failure reason.

### `src/agent/managers/task_manager.py`

- Add atomic updates, locking, and task schema validation.
- Prevent conflicting claims and inconsistent dependency states.
- Add task history or event logs.

### `src/agent/managers/message_bus.py`

- Add safe concurrent read/write handling.
- Introduce message IDs, acknowledgement semantics, and replay protection.
- Add retention controls and delivery observability.

### `src/agent/managers/teammate_manager.py`

- Improve teammate lifecycle control with graceful shutdown and restart support.
- Persist teammate state and last-known activity.
- Add protections against runaway loops or excessive autonomous actions.

## Production Readiness Definition

This project should be considered production ready only when it can:

- Fail safely
- Recover predictably
- Protect sensitive data
- Explain what happened through logs and metrics
- Behave consistently under concurrency
- Be tested and deployed repeatably

Until then, it is best described as an experimental but promising agent framework.
