# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a client-server architecture for the Claude Agent SDK that separates SDK logic into a stateful API server and provides lightweight clients (CLI and web). The server wraps the Claude Agent SDK, manages multiple concurrent sessions, handles permissions, and provides RESTful endpoints.

## Development Commands

### Server

```bash
# Start the API server (development)
uv run backend/server.py

# Start the API server (production, on 0.0.0.0:8080)
./serve

# Quick start script with checks
./start.sh

# With uvicorn for hot reload
uv run uvicorn backend.server:app --host 127.0.0.1 --port 8000 --reload
```

### CLI Client

```bash
# Start interactive CLI client
uv run cli_client/client.py

# With custom server URL
uv run cli_client/client.py --server http://localhost:8000

# With LiteLLM proxy mode and custom model
uv run cli_client/client.py --proxy --model gpt-4
```

### Web Client

```bash
cd web_client
npm install        # First time only
npm run dev        # Development server on port 8080
npm run build      # Production build
npm run preview    # Preview production build
```

### Docker

```bash
# Build from docker directory
cd docker
docker build -t claude-agent-api-server:latest -f Dockerfile ..

# Run container
docker run -d -p 8080:8080 \
  -e ANTHROPIC_AUTH_TOKEN=your_key \
  --name claude-agent-api-server \
  claude-agent-api-server:latest

# Using Docker Compose
cd docker
docker-compose up -d
docker-compose logs -f
docker-compose down
```

### Dependency Management

```bash
# Install dependencies
uv sync

# Reinstall dependencies
uv sync --reinstall

# Run Python code with uv
uv run <script.py>
```

## Architecture

### Core Components

The codebase is organized into three main layers:

1. **Backend Server** (`backend/`): FastAPI server that wraps the Claude Agent SDK
   - `server.py`: Main FastAPI app, lifespan management, CORS, router registration
   - `core/session.py`: `AgentSession` class - manages a single SDK client connection, handles permission callbacks, tracks conversation state
   - `core/session_manager.py`: `SessionManager` class - manages multiple concurrent sessions, creates/resumes/lists/closes sessions
   - `core/workspace_sync.py`: Workspace sync utilities for S3 synchronization using s5cmd
   - `api/sessions.py`: Session CRUD endpoints (create, list, get history, server info, close)
   - `api/messages.py`: Message endpoints (send, status, model control, interrupt, permission mode)
   - `api/permissions.py`: Permission approval endpoint
   - `api/workspace.py`: Workspace sync endpoints (init from S3, sync to S3, workspace info)
   - `api/invocations.py`: Unified invocation endpoint (single entry point for all operations, useful for AWS Lambda)
   - `proxy/litellm_proxy.py`: LiteLLM proxy endpoint (`/v1/messages`) for multi-provider support
   - `models/schemas.py`: Pydantic request/response models

2. **CLI Client** (`cli_client/client.py`): Lightweight interactive command-line client with no SDK dependencies

3. **Web Client** (`web_client/`): React-based web UI with Vite bundler

### Session Lifecycle

1. Client sends POST to `/sessions` with optional parameters (model, proxy mode, working directory)
2. Server creates `AgentSession` and connects Claude Agent SDK client
3. Client sends messages, server processes through SDK and returns responses
4. Background polling for permission requests (permission callback pattern)
5. Client sends DELETE to close session, server disconnects and cleans up

### Permission Flow

- SDK calls `permission_callback()` on `AgentSession` when tools need approval
- Session stores pending permission with `asyncio.Event` and waits
- Client polls `/sessions/{id}/status` to detect pending permissions
- Client presents permission request to user
- User responds via `/sessions/{id}/permissions/respond`
- Session resolves permission and SDK continues execution
- Read-only tools (Read, Glob, Grep) are auto-allowed

### State Management

- `SessionManager`: Global singleton managing all sessions
- `AgentSession`: Individual session with SDK client, permission state, conversation metadata
- Sessions stored in memory (not persisted in database)
- Session files are managed by Claude Agent SDK in `~/.claude/projects/`

### Proxy Mode (LiteLLM Integration)

When `enable_proxy=true` in session creation:
- Sets `ANTHROPIC_BASE_URL` to server's `/v1/messages` endpoint
- Sets `CLAUDE_CODE_USE_BEDROCK=0` (disables AWS Bedrock)
- Sets `ANTHROPIC_AUTH_TOKEN=placeholder` (required by SDK but not used)
- If `background_model` provided, sets `ANTHROPIC_DEFAULT_HAIKU_MODEL`
- Server automatically removes `cache_control` fields for non-Claude models
- Allows using OpenAI, Azure, Cohere, etc. via LiteLLM

## Important Implementation Details

### Session Working Directory

Sessions are associated with a working directory (`cwd`). When resuming sessions or listing available sessions:
- Session files are stored in `~/.claude/projects/<path-key>/<session_id>.jsonl`
- `path-key` is derived from `cwd` by replacing `/` and `_` with `-`
- If `cwd` is provided, only sessions from that project directory are shown
- See `backend/core/session.py` (connect method) and `backend/core/session_manager.py` (list_available_sessions)

### Model Switching

- Use `POST /sessions/{id}/model` to change model at runtime
- Environment variables set during session creation cannot be changed mid-session
- Server automatically handles `cache_control` removal for non-Claude models

### Permission Modes

Available permission modes (set via `POST /sessions/{id}/permission_mode`):
- `default`: Ask for permission on write operations
- `acceptEdits`: Auto-accept Edit tool operations
- `plan`: Plan mode (no execution)
- `bypassPermissions`: Accept all operations (dangerous)

### API Entry Points

Two patterns for API access:
1. **Direct endpoints**: Standard REST pattern (`/sessions`, `/sessions/{id}/messages`, etc.)
2. **Unified invocations**: Single endpoint `/invocations` that routes based on `path` and `method` in payload (useful for AWS Lambda or API gateways)

### Workspace Management

The server includes workspace management features for setting up and syncing user workspaces:

**Git Repository Cloning**:
- **Clone Git**: `POST /workspace/clone-git` - Clone Git repository into user workspace
- Supports HTTPS and SSH URLs
- Optional branch selection and shallow cloning
- Automatic cleanup on error

**S3 Synchronization**:
- **Init from S3**: `POST /workspace/init` - Download user workspace from S3 to local filesystem
- **Sync to S3**: `POST /workspace/sync-to-s3` - Upload local workspace back to S3
- **Workspace Info**: `GET /workspace/info/{user_id}` - Get workspace details (size, file count)
- Uses **s5cmd** for high-performance parallel transfers (10-100x faster than AWS CLI)

**Configuration**:
- Environment variables: `S3_WORKSPACE_BUCKET`, `S3_WORKSPACE_PREFIX`, `WORKSPACE_BASE_PATH`
- S3 path format: `s3://{bucket}/{prefix}/{user_id}/{workspace_name}/`
- Local path format: `{base_path}/{user_id}/`
- See `WORKSPACE_SYNC.md` for detailed documentation

## Testing

### Manual API Testing

```bash
# Health check
curl http://localhost:8000/health

# Create session
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-3-5-sonnet-20241022"}'

# Send message (replace SESSION_ID)
curl -X POST http://localhost:8000/sessions/SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, Claude!"}'

# Get status
curl http://localhost:8000/sessions/SESSION_ID/status

# Close session
curl -X DELETE http://localhost:8000/sessions/SESSION_ID

# Clone git repository
curl -X POST http://localhost:8000/workspace/clone-git \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "git_url": "https://github.com/user/repo.git"}'

# Initialize workspace from S3
curl -X POST http://localhost:8000/workspace/init \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}'

# Get workspace info
curl http://localhost:8000/workspace/info/user123
```

### API Documentation

When server is running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Common Issues

### Session Disconnect Errors

When closing sessions, you may see `RuntimeError` about "cancel scope" or "different task" in anyio/asyncio. This is handled in `AgentSession.disconnect()` - the error is logged as a warning but doesn't fail the operation.

### Permission Request Timeout

Permission requests timeout after 5 minutes (300 seconds). If client doesn't respond, the request is auto-denied.

### Model Compatibility

Non-Claude models require `cache_control` fields to be removed. The server handles this automatically in the LiteLLM proxy endpoint for models that don't contain "claude" in their ID.

### Working Directory Session Discovery

When resuming sessions, the SDK expects full file paths. The session manager searches:
1. Exact `cwd`-based path if `cwd` is provided
2. All project directories as fallback
3. Returns 404 if session file not found

## Dependencies

Core dependencies (managed via `pyproject.toml` and `uv`):
- `claude-agent-sdk>=0.1.5`: Claude Agent SDK
- `fastapi>=0.120.0`: Web framework
- `litellm>=1.78.7`: Multi-provider LLM proxy
- `boto3>=1.40.58`: AWS SDK (for Bedrock support)
- `langfuse>=2,<3`: Observability (optional)

External tools:
- `s5cmd`: High-performance S3 transfer tool (required for workspace sync)

Web client dependencies:
- React 19.2.0
- Vite 7.1.12
- lucide-react (icons)

## Code Style

- Python files use English comments and type hints
- Async/await throughout backend
- Pydantic models for request/response validation
- Error handling with FastAPI HTTPException
- Session cleanup on shutdown via lifespan context manager
