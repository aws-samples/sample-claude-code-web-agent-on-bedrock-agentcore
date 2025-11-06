"""
Session Management Endpoints.

Provides REST API endpoints for session CRUD operations including
creating, listing, and closing sessions.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

from ..core import SessionManager
from ..models import (
    CreateSessionRequest,
    CreateSessionResponse,
    ListSessionsResponse,
)

router = APIRouter()


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    from ..server import session_manager

    return session_manager


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    Create a new session or resume an existing one.

    Args:
        request: Session creation request

    Returns:
        Session information
    """
    manager = get_session_manager()
    session_id = await manager.create_session(
        user_id=request.user_id,
        resume_session_id=request.resume_session_id,
        model=request.model,
        background_model=request.background_model,
        enable_proxy=request.enable_proxy,
        server_port=8080,  # Using hardcoded port from uvicorn.run
        cwd=request.cwd,
    )

    return CreateSessionResponse(
        session_id=session_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        status="connected",
    )


@router.get("/sessions", response_model=ListSessionsResponse)
async def list_sessions(cwd: Optional[str] = None):
    """
    List all active sessions, optionally filtered by cwd.

    Args:
        cwd: Optional working directory to filter by

    Returns:
        List of active sessions
    """
    manager = get_session_manager()
    sessions = manager.list_sessions(cwd=cwd)
    return ListSessionsResponse(sessions=sessions)


@router.get("/sessions/available")
async def list_available_sessions(cwd: Optional[str] = None):
    """
    List all available sessions from disk, optionally filtered by cwd.

    Args:
        cwd: Optional working directory to filter by

    Returns:
        List of available sessions
    """
    manager = get_session_manager()
    sessions = manager.list_available_sessions(cwd=cwd)
    return {"sessions": sessions}


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str, cwd: Optional[str] = None):
    """
    Get the conversation history for a session from disk.

    Args:
        session_id: The session ID
        cwd: Optional current working directory to locate the session file

    Returns:
        Session history with messages and metadata
    """
    base_dir = Path.home() / ".claude" / "projects"

    # Find the session file
    session_file = None

    # If cwd is provided, try to find it directly
    if cwd:
        path_key = cwd.replace("/", "-").replace("_", "-")
        potential_file = base_dir / path_key / f"{session_id}.jsonl"
        if potential_file.exists():
            session_file = potential_file

    # If not found, search all project directories
    if not session_file:
        for project_dir in base_dir.iterdir():
            if not project_dir.is_dir():
                continue
            potential_file = project_dir / f"{session_id}.jsonl"
            if potential_file.exists():
                session_file = potential_file
                break

    if not session_file:
        raise HTTPException(status_code=404, detail="Session history not found")

    try:
        messages = []
        metadata = {
            "session_id": session_id,
            "cwd": None,
            "git_branch": None,
            "version": None,
        }

        with open(session_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                    entry_type = entry.get("type")

                    # Extract metadata from first entry
                    if not metadata["cwd"]:
                        metadata["cwd"] = entry.get("cwd")
                        metadata["git_branch"] = entry.get("gitBranch")
                        metadata["version"] = entry.get("version")

                    # Process user and assistant messages
                    if entry_type in ["user", "assistant"]:
                        msg_data = entry.get("message", {})
                        role = msg_data.get("role")
                        content = msg_data.get("content")

                        # Handle different content formats
                        if isinstance(content, str):
                            # Simple text message
                            messages.append(
                                {
                                    "role": role,
                                    "content": content,
                                    "timestamp": entry.get("timestamp"),
                                    "uuid": entry.get("uuid"),
                                }
                            )
                        elif isinstance(content, list):
                            # Content blocks - process each separately
                            for block in content:
                                if isinstance(block, dict):
                                    block_type = block.get("type")

                                    if block_type == "text":
                                        # Regular text block
                                        messages.append(
                                            {
                                                "role": role,
                                                "content": block.get("text", ""),
                                                "timestamp": entry.get("timestamp"),
                                                "uuid": entry.get("uuid"),
                                            }
                                        )
                                    elif block_type == "tool_use":
                                        # Tool use block
                                        messages.append(
                                            {
                                                "type": "tool_use",
                                                "role": role,
                                                "tool_name": block.get("name"),
                                                "tool_input": block.get("input"),
                                                "tool_use_id": block.get("id"),
                                                "timestamp": entry.get("timestamp"),
                                                "uuid": entry.get("uuid"),
                                            }
                                        )
                                    elif block_type == "tool_result":
                                        # Tool result block
                                        messages.append(
                                            {
                                                "type": "tool_result",
                                                "role": role,
                                                "tool_use_id": block.get("tool_use_id"),
                                                "content": block.get("content"),
                                                "is_error": block.get("is_error", False),
                                                "timestamp": entry.get("timestamp"),
                                                "uuid": entry.get("uuid"),
                                            }
                                        )
                                elif isinstance(block, str):
                                    # String block
                                    messages.append(
                                        {
                                            "role": role,
                                            "content": block,
                                            "timestamp": entry.get("timestamp"),
                                            "uuid": entry.get("uuid"),
                                        }
                                    )
                        else:
                            # Unknown format, convert to string
                            messages.append(
                                {
                                    "role": role,
                                    "content": str(content),
                                    "timestamp": entry.get("timestamp"),
                                    "uuid": entry.get("uuid"),
                                }
                            )

                except json.JSONDecodeError:
                    continue

        return {
            "metadata": metadata,
            "messages": messages,
            "message_count": len(messages),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read session history: {str(e)}"
        )


@router.get("/sessions/{session_id}/server_info")
async def get_server_info(session_id: str):
    """
    Get server initialization info for a session.

    Args:
        session_id: The session ID

    Returns:
        Server info dictionary with commands, output styles, etc.
    """
    manager = get_session_manager()
    session = manager.get_session(session_id)
    info = await session.get_server_info()
    return info


@router.delete("/sessions/{session_id}")
async def close_session(session_id: str):
    """
    Close a session.

    Args:
        session_id: The session ID

    Returns:
        Success message
    """
    manager = get_session_manager()
    await manager.close_session(session_id)
    return {"status": "closed"}
