# API Server Architecture

This document describes the refactored architecture of the Claude Agent API Server.

## Overview

The server has been refactored from a single monolithic file (1351 lines) into a well-organized modular structure for better maintainability, testability, and scalability.

## Directory Structure

```
backend/
├── server.py                    # Main FastAPI app (~110 lines)
├── models/                      # Data models
│   ├── __init__.py
│   └── schemas.py              # Pydantic request/response models (~120 lines)
├── core/                        # Business logic
│   ├── __init__.py
│   ├── session.py              # AgentSession class (~420 lines)
│   └── session_manager.py      # SessionManager class (~200 lines)
├── api/                         # API endpoints
│   ├── __init__.py
│   ├── sessions.py             # Session CRUD endpoints (~230 lines)
│   ├── messages.py             # Message/status endpoints (~130 lines)
│   ├── permissions.py          # Permission endpoints (~50 lines)
│   └── invocations.py          # Unified invocation endpoint (~180 lines)
└── proxy/                       # LiteLLM integration
    ├── __init__.py
    └── litellm_proxy.py        # Proxy endpoint (~130 lines)

cli_client/                      # CLI client
└── client.py                   # Interactive CLI (~700 lines)

web_client/                      # Web UI
└── src/                        # React components
```

## Module Descriptions

### `server.py`
The main entry point that:
- Creates the FastAPI application
- Configures CORS middleware
- Registers all routers
- Manages application lifespan (startup/shutdown)
- Provides health check endpoint

### `models/schemas.py`
Contains all Pydantic models for:
- Request validation (CreateSessionRequest, SendMessageRequest, etc.)
- Response serialization (CreateSessionResponse, SendMessageResponse, etc.)
- Data transfer objects (SessionInfo, SessionStatus, etc.)

### `core/session.py`
Implements the `AgentSession` class which:
- Manages a single Claude Agent SDK client connection
- Handles permission callbacks and permission state
- Processes messages and tool usage
- Tracks session metadata (created_at, last_activity, message_count)
- Supports model switching and interruption

### `core/session_manager.py`
Implements the `SessionManager` class which:
- Manages multiple concurrent sessions
- Creates and resumes sessions
- Lists active sessions (filtered by working directory)
- Lists available sessions from disk
- Handles session cleanup

### `api/sessions.py`
Provides REST endpoints for:
- Creating new sessions (`POST /sessions`)
- Listing active sessions (`GET /sessions`)
- Listing available sessions from disk (`GET /sessions/available`)
- Getting session history (`GET /sessions/{id}/history`)
- Getting server info (`GET /sessions/{id}/server_info`)
- Closing sessions (`DELETE /sessions/{id}`)

### `api/messages.py`
Provides REST endpoints for:
- Sending messages (`POST /sessions/{id}/messages`)
- Getting session status (`GET /sessions/{id}/status`)
- Setting model (`POST /sessions/{id}/model`)
- Interrupting session (`POST /sessions/{id}/interrupt`)
- Setting permission mode (`POST /sessions/{id}/permission_mode`)

### `api/permissions.py`
Provides REST endpoints for:
- Responding to permission requests (`POST /sessions/{id}/permissions/respond`)

### `api/invocations.py`
Provides a unified invocation endpoint:
- Single entry point for all operations (`POST /invocations`)
- Routes requests based on path and method
- Useful for AWS Lambda or other gateway patterns

### `proxy/litellm_proxy.py`
Provides LiteLLM proxy functionality:
- Anthropic-compatible Messages API endpoint (`POST /v1/messages`)
- Supports streaming and non-streaming responses
- Forwards requests to LiteLLM for multi-provider support
- Automatically removes cache_control for non-Claude models

## Benefits of the New Architecture

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Maintainability**: Smaller files are easier to understand and modify
3. **Testability**: Individual components can be tested in isolation
4. **Scalability**: New features can be added without modifying existing code
5. **Reusability**: Core components can be imported and used in other contexts
6. **Code Navigation**: Developers can quickly find relevant code by module

## Migration Notes

- The original monolithic `server.py` was split into modular components
- All functionality remains the same
- No changes needed to API clients
- Directory renamed from `src/` to `backend/` for clarity
- CLI client moved to root-level `cli_client/` directory

## Testing

To verify the refactored server:

```bash
# Test imports
python -c "from backend.server import app; print('✓ Server imports successfully')"

# Run the server
python -m backend.server

# Or use uvicorn
uvicorn backend.server:app --host 127.0.0.1 --port 8000

# Or use the start script
./start.sh
```

## Future Improvements

Potential enhancements for the architecture:

1. Add dependency injection for SessionManager
2. Extract configuration into a separate config module
3. Add comprehensive unit tests for each module
4. Add API versioning support (v1, v2, etc.)
5. Add middleware for request logging and metrics
6. Add OpenAPI documentation enhancements
7. Add rate limiting and authentication middleware
