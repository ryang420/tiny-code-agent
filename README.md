# tiny-code-agent

A modular autonomous code agent for experimentation with multi-agent collaboration, task management, and context compression.

## Features

- **Multi-agent collaboration**: Spawn autonomous teammates that work together
- **Task management**: Persistent file-based tasks with dependencies
- **Context compression**: Automatic conversation compression at 100k tokens
- **Background execution**: Run long-running commands in background threads
- **Skills system**: Load specialized knowledge from modular skill definitions
- **Message bus**: Inter-agent communication via JSONL inbox system
- **Subagent delegation**: Spawn isolated agents for exploration or work

## Quick Start

```bash
# Setup
cp .env.example .env
# Edit .env to add your provider credentials and MODEL_ID

# Install dependencies
pip install -r requirements.txt

# Run the agent
python src/main.py
```

## Architecture

The agent is built with a modular architecture:

- **Core**: Base tools (file ops, bash) and subagent spawning
- **Managers**: Task, todo, background, message bus, teammate, and skill management
- **Utils**: Context compression and coordination protocols
- **Agent**: Main loop with tool dispatch and LLM integration

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation.

## REPL Commands

- `/compact` - Manually compress conversation context
- `/tasks` - List all tasks
- `/team` - List teammates and their status
- `/inbox` - Check inbox messages
- `q` or `exit` - Quit

## Configuration

Required environment variables:
- `MODEL_ID` - Model to use (e.g., `claude-sonnet-4-6`)

Optional:
- `LLM_PROVIDER` - Force `anthropic` or `openai`
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `ANTHROPIC_BASE_URL` - For Anthropic-compatible providers
- `OPENAI_API_KEY` - Your OpenAI API key
- `OPENAI_BASE_URL` - For OpenAI-compatible providers

Provider selection:
- If `LLM_PROVIDER=openai`, requests use OpenAI Chat Completions format.
- If `LLM_PROVIDER=anthropic`, requests use Anthropic Messages format.
- If `LLM_PROVIDER` is unset, the app auto-selects OpenAI when `OPENAI_API_KEY` or `OPENAI_BASE_URL` is present; otherwise it uses Anthropic.

See `.env.example` for supported providers and their benchmark scores.

## Project Structure

```
src/
├── agent/
│   ├── core/              # Base tools and subagent
│   ├── managers/          # Manager classes
│   ├── utils/             # Utilities
│   └── agent.py           # Main agent loop
├── main.py                # REPL entry point
```

## Development

```bash
# Run tests
pytest

```

## License

Experimental project for research purposes.
