# Quick Start Guide

Get up and running with the Claude Agent API Server in 5 minutes.

## Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- Claude Code CLI installed: `npm install -g @anthropic-ai/claude-code`

## Installation

### 1. Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

### 2. Install Dependencies

```bash
# From the workspace root (claude-agent-sdk-python)
cd /path/to/claude-agent-sdk-python
uv sync

# This will install both the SDK and api_server dependencies
```

## Running the Server and Client

### Option 1: Using uv (Recommended)

```bash
# Terminal 1: Start the server
cd api_server
uv run backend/server.py
```

```bash
# Terminal 2: Start the client
cd api_server
uv run cli_client/client.py
```

### Option 2: Using the Start Script

```bash
# Terminal 1: Start the server
cd api_server
./start.sh
```

```bash
# Terminal 2: Start the client
cd api_server
uv run cli_client/client.py
```

## First Conversation

Once the client is running:

```
👤 You: Hello! What can you help me with?
🤖 Claude: [Claude's response]

👤 You: List files in the current directory
🔧 Using tool: Bash
🤖 Claude: [Results]
```

## Common Commands

- `help` - Show help information
- `sessions` - List available sessions
- `clear` - Start a new session
- `exit` - Exit the program

## Permission Approval

When Claude needs to use a write operation:

```
⚠️  Permission Request
Tool: Bash
Command: ls -la

Allow? [Y/n/d]:
```

- Press `Y` or `Enter` to approve
- Press `n` to deny
- Press `d` to see details
- Press `a` to apply suggestions (if available)

## Testing the API

Test the API using curl or the clients:

```bash
# Test with curl
curl http://localhost:8000/health

# Or use the CLI client
uv run cli_client/client.py

# Or use the web client
cd web_client && npm run dev
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Architecture

```
Clients (CLI/Web) ←→ HTTP API ←→ Backend Server ←→ Claude Agent SDK
```

- **Clients**: CLI (cli_client/) and Web UI (web_client/)
- **Backend**: Stateful API server (backend/)
- **SDK**: Claude Agent SDK for Claude Code

## Troubleshooting

### "Cannot connect to server"

Make sure the server is running:
```bash
curl http://localhost:8000/health
```

### "Claude Code CLI not found"

Install the CLI:
```bash
npm install -g @anthropic-ai/claude-code
```

### Import errors

Make sure all dependencies are installed:
```bash
# From workspace root
uv sync

# Or reinstall if needed
uv sync --reinstall
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check out the API docs at http://localhost:8000/docs
- Try the web client for a modern UI experience

## File Structure

```
api_server/
├── backend/
│   ├── api/                  # API endpoints
│   ├── core/                 # Business logic
│   ├── models/               # Data models
│   ├── proxy/                # LiteLLM proxy
│   └── server.py             # FastAPI server
├── cli_client/
│   └── client.py             # CLI client
├── web_client/               # Web UI
├── pyproject.toml            # Project config (uv managed)
├── uv.lock                   # Dependency lock file
├── start.sh                  # Quick start script
├── README.md                 # Full documentation
├── QUICKSTART.md             # This file
└── ARCHITECTURE.md           # Architecture details
```

## Key Features

✅ **Multi-session support** - Run multiple conversations simultaneously
✅ **Permission control** - Approve tool usage interactively
✅ **Session persistence** - Resume previous conversations
✅ **Stateful API** - Server manages all SDK state
✅ **Lightweight client** - No SDK dependencies in client
✅ **RESTful API** - Easy integration with other tools

Happy coding! 🚀
