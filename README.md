# Claude Agent API Server

A client-server architecture for the Claude Agent SDK that separates SDK logic into a stateful API server and provides lightweight clients (CLI and web).

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- Node.js 18+ (for web client)

### Installation

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Start the server
uv run backend/server.py

# Or use the convenience script
./start.sh
```

### Usage

**CLI Client:**
```bash
uv run cli_client/client.py
```

**Web Client:**
```bash
cd web_client
npm install
npm run dev
```

Visit http://localhost:8080 to use the web interface.

**Production Deployment:**
```bash
./serve  # Runs on 0.0.0.0:8080
```

## Features

- Multi-session support with session restoration
- RESTful API with FastAPI
- Interactive CLI and web clients
- Permission callback system
- LiteLLM proxy for multi-provider support
- Workspace management with S3 sync
- Docker support

## Documentation

For detailed documentation, see the `claude/` directory:

- **[Quick Start Guide](claude/quickstart.md)** - Get started quickly
- **[Architecture](claude/architecture.md)** - System design and components
- **[Workspace Sync](claude/workspace-sync.md)** - S3 workspace management
- **[Web Client](claude/web-client/readme.md)** - Web interface documentation
- **[User Registration](claude/cognito-signup-guide.md)** - AWS Cognito user signup configuration
- **[CLI Client](claude/cli-client/readme.md)** - Command-line interface
- **[Docker](claude/docker/readme.md)** - Container deployment

## API Endpoints

- `POST /sessions` - Create new session
- `POST /sessions/{id}/messages` - Send message
- `GET /sessions/{id}/status` - Get status
- `POST /invocations` - Unified invocation endpoint
- `GET /health` - Health check

Full API documentation: http://localhost:8000/docs (when server is running)

## Development

```bash
# Start server with hot reload
uv run uvicorn backend.server:app --host 127.0.0.1 --port 8000 --reload

# Run tests
uv run pytest

# Format code
uv run ruff format backend/
```

## License

Same as the parent Claude Agent SDK project.
