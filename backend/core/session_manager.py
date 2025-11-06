"""
Session Manager.

This module contains the SessionManager class which manages multiple
concurrent Claude Agent sessions, handling creation, restoration,
and cleanup operations.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException

from ..models import SessionInfo
from .session import AgentSession


class SessionManager:
    """
    Manages multiple concurrent Claude Agent sessions.

    Each session maintains its own SDK client, conversation history,
    and permission state. Supports session creation, restoration,
    and cleanup.
    """

    def __init__(self):
        """Initialize the session manager."""
        self.sessions: dict[str, AgentSession] = {}
        self.session_dir = Path.home() / ".claude" / "projects"

    async def create_session(
        self,
        user_id: Optional[str] = None,
        resume_session_id: Optional[str] = None,
        model: Optional[str] = None,
        background_model: Optional[str] = None,
        enable_proxy: bool = False,
        server_port: int = 8080,
        cwd: Optional[str] = None,
    ) -> str:
        """
        Create a new session or resume an existing one.

        Args:
            user_id: User ID for S3 sync tracking
            resume_session_id: Optional session ID to resume
            model: Optional model name override
            background_model: Optional background model for agents
            enable_proxy: Enable LiteLLM proxy mode
            server_port: Server port for proxy mode
            cwd: Working directory for the session

        Returns:
            The session ID (new or resumed)
        """
        session_id = resume_session_id or str(__import__("uuid").uuid4())

        if session_id in self.sessions:
            raise HTTPException(status_code=400, detail="Session already active")

        session = AgentSession(
            session_id,
            user_id,
            model,
            background_model,
            enable_proxy,
            server_port,
            cwd,
        )
        await session.connect(resume_session_id)

        self.sessions[session_id] = session

        if user_id:
            from .claude_sync_manager import get_claude_sync_manager
            sync_manager = get_claude_sync_manager()
            if sync_manager:
                sync_manager._synced_users.add(user_id)

                if cwd and cwd.startswith("/workspace/") and cwd != "/workspace":
                    project_name = cwd.replace("/workspace/", "")
                    if "/" not in project_name:
                        sync_manager.set_user_project(user_id, project_name)

        return session_id

    def get_session(self, session_id: str) -> AgentSession:
        """
        Get an active session by ID.

        Args:
            session_id: The session ID

        Returns:
            The AgentSession instance

        Raises:
            HTTPException: If session not found
        """
        if session_id not in self.sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        return self.sessions[session_id]

    async def close_session(self, session_id: str):
        """
        Close and cleanup a session.

        Args:
            session_id: The session ID to close
        """
        if session_id in self.sessions:
            session = self.sessions[session_id]
            await session.disconnect()
            del self.sessions[session_id]

    def list_sessions(self, cwd: Optional[str] = None) -> list[SessionInfo]:
        """
        List all active sessions, optionally filtered by cwd.

        Args:
            cwd: Optional working directory to filter by

        Returns:
            List of SessionInfo objects
        """
        result = []
        for session_id, session in self.sessions.items():
            # Filter by cwd if provided
            if cwd and session.cwd != cwd:
                continue

            result.append(
                SessionInfo(
                    session_id=session_id,
                    created_at=session.created_at.isoformat(),
                    last_activity=session.last_activity.isoformat(),
                    status=session.status,
                    message_count=session.message_count,
                    cwd=session.cwd,
                )
            )
        return result

    def list_available_sessions(
        self, cwd: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        List all available sessions from disk, optionally filtered by cwd.

        Args:
            cwd: Optional working directory to filter by

        Returns:
            List of session information dictionaries
        """
        sessions = []

        if not self.session_dir.exists():
            return sessions

        # If cwd is provided, only scan that specific project directory
        if cwd:
            path_key = cwd.replace("/", "-").replace("_", "-")
            project_dirs = [self.session_dir / path_key]
        else:
            # Scan all project directories
            project_dirs = list(self.session_dir.iterdir())

        for project_dir in project_dirs:
            if not project_dir.exists() or not project_dir.is_dir():
                continue

            for session_file in project_dir.glob("*.jsonl"):
                try:
                    session_id = session_file.stem

                    # Skip SDK internal sessions (agent-xxxxxxxx format)
                    # These are created by Claude Agent SDK and not user-visible
                    if session_id.startswith("agent-"):
                        continue

                    mtime = session_file.stat().st_mtime
                    modified = datetime.fromtimestamp(mtime, tz=timezone.utc)

                    # Read file to check if it has actual content
                    preview = "No preview"
                    summary = None
                    message_count = 0
                    first_user_message = None

                    with open(session_file, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue

                            try:
                                entry = json.loads(line)
                                entry_type = entry.get("type")

                                # Count actual user/assistant messages
                                if entry_type in ["user", "assistant"]:
                                    message_count += 1

                                    # Get first user message for preview
                                    if entry_type == "user" and not first_user_message:
                                        msg = entry.get("message", {})
                                        content = msg.get("content", "")
                                        if isinstance(content, str):
                                            first_user_message = content
                                        elif isinstance(content, list) and len(content) > 0:
                                            # Extract text from first content block
                                            first_block = content[0]
                                            if isinstance(first_block, dict):
                                                first_user_message = first_block.get("text", "")
                                            elif isinstance(first_block, str):
                                                first_user_message = first_block

                                # Check for summary
                                if entry_type == "summary" and not summary:
                                    summary = entry.get("summary", "")
                            except json.JSONDecodeError:
                                continue

                    # Use summary if available, otherwise use first user message
                    if summary:
                        preview = summary[:100]
                    elif first_user_message:
                        preview = first_user_message[:100]

                    sessions.append(
                        {
                            "session_id": session_id,
                            "modified": modified.isoformat(),
                            "preview": preview,
                            "project": project_dir.name,
                            "message_count": message_count,
                            "first_message": first_user_message[:100] if first_user_message else None,
                        }
                    )
                except Exception:
                    continue

        # Sort by modification time
        sessions.sort(key=lambda x: x["modified"], reverse=True)
        return sessions
