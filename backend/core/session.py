"""
Agent Session Management.

This module contains the AgentSession class which represents a single
interactive session with the Claude Agent SDK, managing the client
connection, permission callbacks, and conversation state.
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    CLINotFoundError,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    TextBlock,
    ToolPermissionContext,
    ToolUseBlock,
    UserMessage,
)

from ..models import MessageBlock, PermissionRequest, SendMessageResponse, SessionStatus


def load_custom_system_prompt() -> Optional[str]:
    """
    Load custom system prompt from backend/claude_system_prompt.md.

    Returns:
        The content of the file if it exists, None otherwise.
    """
    try:
        # Get the backend directory path
        backend_dir = Path(__file__).parent.parent
        prompt_file = backend_dir / "claude_system_prompt.md"

        if prompt_file.exists():
            with open(prompt_file, encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
    except Exception as e:
        # Log error but don't fail session creation
        import logging
        logging.warning(f"Failed to load custom system prompt: {e}")

    return None


class AgentSession:
    """
    Represents a single Claude Agent session.

    Manages the SDK client, permission callbacks, and conversation state
    for one interactive session.
    """

    def __init__(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
        background_model: Optional[str] = None,
        enable_proxy: bool = False,
        server_port: int = 8080,
        cwd: Optional[str] = None,
    ):
        """
        Initialize an agent session.

        Args:
            session_id: Unique session identifier
            user_id: User ID for S3 sync tracking
            model: Optional model name (defaults to ANTHROPIC_MODEL env var)
            background_model: Optional background model for agents
            enable_proxy: Enable LiteLLM proxy mode (sets ANTHROPIC_BASE_URL)
            server_port: Server port for proxy mode (default: 8000)
            cwd: Working directory for the session
        """
        self.session_id = session_id
        self.user_id = user_id
        self.client: Optional[ClaudeSDKClient] = None
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)
        self.status = "initializing"
        self.message_count = 0

        # Permission management
        self.pending_permission: Optional[dict[str, Any]] = None
        self.permission_event: Optional[asyncio.Event] = None
        self.permission_result: Optional[Any] = None

        # Session configuration
        self.cwd = cwd
        # Model: use provided, or env var, or None (SDK default)
        self.model = model or os.environ.get("ANTHROPIC_MODEL")
        self.background_model = background_model  # Background model for agents
        self.current_model = self.model  # Track current model for status

        # Proxy configuration
        self.enable_proxy = enable_proxy
        self.server_port = server_port

        # Server info cache
        self.server_info: Optional[dict[str, Any]] = None

    async def connect(self, resume_session_id: Optional[str] = None):
        """
        Connect the SDK client and initialize the session.

        Args:
            resume_session_id: Optional session ID to resume from
        """
        print(f"\n[Session] {'Resuming' if resume_session_id else 'Creating'} session {self.session_id}")
        print(f"[Session] user_id: {self.user_id}")
        print(f"[Session] cwd: {self.cwd}")
        print(f"[Session] model: {self.model}")
        print(f"[Session] background_model: {self.background_model}")
        print(f"[Session] enable_proxy: {self.enable_proxy}")
        if resume_session_id:
            print(f"[Session] resume_session_id: {resume_session_id}")

        # Load custom system prompt from file
        custom_prompt = load_custom_system_prompt()

        # Build system prompt configuration
        # Use preset (Claude Code default) with custom append if available
        if custom_prompt:
            system_prompt_config = {
                "type": "preset",
                "preset": "claude_code",
                "append": custom_prompt,
            }
        else:
            # Use preset without custom append
            system_prompt_config = {
                "type": "preset",
                "preset": "claude_code",
            }

        options_dict = {
            "allowed_tools": ["Read", "Glob", "Grep"],
            "system_prompt": system_prompt_config,
            "max_turns": 0,
            "can_use_tool": self.permission_callback,
            "permission_mode": "default",
        }

        if resume_session_id:
            # SDK expects full path to session file, not just session ID
            # Construct the path based on cwd
            if self.cwd:
                path_key = self.cwd.replace("/", "-").replace("_", "-")
                session_file = (
                    Path.home()
                    / ".claude"
                    / "projects"
                    / path_key
                    / f"{resume_session_id}.jsonl"
                )
                if session_file.exists():
                    options_dict["resume"] = str(session_file)
                else:
                    # Fall back to searching all project directories
                    session_dir = Path.home() / ".claude" / "projects"
                    for project_dir in session_dir.iterdir():
                        if not project_dir.is_dir():
                            continue
                        potential_file = project_dir / f"{resume_session_id}.jsonl"
                        if potential_file.exists():
                            options_dict["resume"] = str(potential_file)
                            break
            else:
                # No cwd provided, search all project directories
                session_dir = Path.home() / ".claude" / "projects"
                for project_dir in session_dir.iterdir():
                    if not project_dir.is_dir():
                        continue
                    potential_file = project_dir / f"{resume_session_id}.jsonl"
                    if potential_file.exists():
                        options_dict["resume"] = str(potential_file)
                        break

        if self.model:
            options_dict["model"] = self.model

        if self.cwd:
            options_dict["cwd"] = self.cwd

        # Build environment variables
        env_vars = {}

        # Enable proxy mode by setting ANTHROPIC_BASE_URL
        if self.enable_proxy:
            env_vars["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{self.server_port}"
            # Disable Bedrock when using proxy mode
            env_vars["CLAUDE_CODE_USE_BEDROCK"] = "0"
            # Add placeholder API key (not actually used, just a placeholder)
            env_vars["ANTHROPIC_AUTH_TOKEN"] = "placeholder"

            # If a background model is specified, set it as the default Haiku model for agents
            if self.background_model:
                env_vars["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = self.background_model

        # Add env vars if any were set
        if env_vars:
            options_dict["env"] = env_vars
            print(f"[Session] Environment variables set:")
            for key, value in env_vars.items():
                print(f"[Session]   {key}={value}")
        else:
            print(f"[Session] No custom environment variables")

        options = ClaudeAgentOptions(**options_dict)

        try:
            print(f"[Session] Connecting to Claude SDK...")
            self.client = ClaudeSDKClient(options=options)
            await self.client.connect()
            self.status = "connected"
            print(f"[Session] ✓ Connected successfully")
        except (CLINotFoundError, CLIConnectionError) as e:
            self.status = "error"
            raise HTTPException(status_code=500, detail=f"Failed to connect: {str(e)}")

    async def disconnect(self):
        """Disconnect the SDK client and cleanup."""
        if self.client:
            try:
                await self.client.disconnect()
            except RuntimeError as e:
                # Handle anyio TaskGroup exit in different task error
                # This can happen when closing sessions due to asyncio event loop differences
                if "cancel scope" in str(e) or "different task" in str(e):
                    # Log the error but don't fail - the session is being closed anyway
                    import logging

                    logging.warning(
                        f"Session {self.session_id}: Disconnect cleanup error (non-fatal): {e}"
                    )
                else:
                    raise
            finally:
                self.status = "disconnected"

    async def permission_callback(
        self, tool_name: str, input_data: dict, context: ToolPermissionContext
    ) -> PermissionResultAllow | PermissionResultDeny:
        """
        Permission callback for tool usage.

        This method is called by the SDK when a tool needs permission.
        It creates a pending permission request and waits for the client
        to respond via the API.

        Args:
            tool_name: Name of the tool requesting permission
            input_data: Tool input parameters
            context: Permission context with suggestions

        Returns:
            Permission result (allow or deny)
        """
        # Auto-allow read-only operations
        if tool_name in ["Read", "Glob", "Grep"]:
            return PermissionResultAllow()

        # Create permission request
        request_id = str(uuid.uuid4())
        self.pending_permission = {
            "request_id": request_id,
            "tool_name": tool_name,
            "tool_input": input_data,
            "suggestions": [
                s.__dict__ if hasattr(s, "__dict__") else s for s in context.suggestions
            ],
        }

        # Create event to wait for response
        self.permission_event = asyncio.Event()
        self.permission_result = None

        # Wait for client to respond (with timeout)
        try:
            await asyncio.wait_for(
                self.permission_event.wait(), timeout=300
            )  # 5 minute timeout
        except asyncio.TimeoutError:
            self.pending_permission = None
            return PermissionResultDeny(message="Permission request timed out")

        # Get result
        result = self.permission_result
        self.pending_permission = None
        self.permission_event = None
        self.permission_result = None

        return result

    def respond_to_permission(
        self, request_id: str, allowed: bool, apply_suggestions: bool = False
    ):
        """
        Respond to a pending permission request.

        Args:
            request_id: The permission request ID
            allowed: Whether to allow the operation
            apply_suggestions: Whether to apply permission suggestions

        Raises:
            HTTPException: If no matching pending permission
        """
        if (
            not self.pending_permission
            or self.pending_permission["request_id"] != request_id
        ):
            raise HTTPException(
                status_code=404, detail="No matching permission request"
            )

        if allowed:
            if apply_suggestions and self.pending_permission["suggestions"]:
                # Apply suggestions by converting them back to PermissionUpdate objects
                from claude_agent_sdk import PermissionUpdate

                suggestions = []
                for s in self.pending_permission["suggestions"]:
                    suggestions.append(PermissionUpdate(**s))

                self.permission_result = PermissionResultAllow(
                    updated_permissions=suggestions
                )
            else:
                self.permission_result = PermissionResultAllow()
        else:
            self.permission_result = PermissionResultDeny(message="User denied")

        # Signal that response is ready
        if self.permission_event:
            self.permission_event.set()

    async def send_message(self, message: str) -> SendMessageResponse:
        """
        Send a message and get the response.

        Args:
            message: The user's message

        Returns:
            SendMessageResponse with assistant's reply

        Raises:
            HTTPException: If session not connected
        """
        if not self.client or self.status != "connected":
            raise HTTPException(status_code=400, detail="Session not connected")

        self.last_activity = datetime.now(timezone.utc)
        self.message_count += 1

        # Send message
        await self.client.query(message)

        # Collect response
        messages = []
        cost_usd = None
        num_turns = None

        async for msg in self.client.receive_response():
            if isinstance(msg, UserMessage):
                # Skip user messages in response
                pass
            elif isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        messages.append(MessageBlock(type="text", content=block.text))
                    elif isinstance(block, ToolUseBlock):
                        messages.append(
                            MessageBlock(
                                type="tool_use",
                                tool_name=block.name,
                                tool_input=block.input,
                            )
                        )
            elif isinstance(msg, ResultMessage):
                cost_usd = msg.total_cost_usd
                num_turns = msg.num_turns

        return SendMessageResponse(
            messages=messages,
            session_id=self.session_id,
            cost_usd=cost_usd,
            num_turns=num_turns,
        )

    async def send_message_stream(self, message: str):
        """
        Send a message and stream the response in real-time.

        Args:
            message: The user's message

        Yields:
            Dictionary events with type and data for each step

        Raises:
            HTTPException: If session not connected
        """
        if not self.client or self.status != "connected":
            raise HTTPException(status_code=400, detail="Session not connected")

        self.last_activity = datetime.now(timezone.utc)
        self.message_count += 1

        # Send initial event
        yield {
            "type": "start",
            "session_id": self.session_id,
            "message": message
        }

        # Send message
        await self.client.query(message)

        # Track last reported permission to avoid duplicates
        last_permission_id = None

        # Stream response
        async for msg in self.client.receive_response():
            # Check for pending permission and send event if new
            if self.pending_permission:
                current_permission_id = self.pending_permission.get("request_id")
                if current_permission_id != last_permission_id:
                    yield {
                        "type": "permission",
                        "permission": self.pending_permission
                    }
                    last_permission_id = current_permission_id

            if isinstance(msg, UserMessage):
                # User message event
                yield {
                    "type": "user_message",
                    "content": msg.content
                }
            elif isinstance(msg, AssistantMessage):
                # Assistant message with content blocks
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        yield {
                            "type": "text",
                            "content": block.text
                        }
                    elif isinstance(block, ToolUseBlock):
                        yield {
                            "type": "tool_use",
                            "tool_name": block.name,
                            "tool_input": block.input,
                            "tool_use_id": block.id
                        }
            elif isinstance(msg, ResultMessage):
                # Final result with metadata
                yield {
                    "type": "result",
                    "cost_usd": msg.total_cost_usd,
                    "num_turns": msg.num_turns,
                    "session_id": self.session_id
                }

        # Send completion event
        yield {
            "type": "done",
            "session_id": self.session_id
        }

        from .claude_sync_manager import get_claude_sync_manager
        sync_manager = get_claude_sync_manager()
        if sync_manager:
            asyncio.create_task(sync_manager.backup_after_task(self.user_id))

    async def set_model(self, model: Optional[str]):
        """
        Change the model for this session.

        Args:
            model: Model name to use (None for default)

        Raises:
            HTTPException: If session not connected or SDK call fails
        """
        if not self.client or self.status != "connected":
            raise HTTPException(status_code=400, detail="Session not connected")

        try:
            await self.client.set_model(model)
            self.current_model = model
            self.model = model  # Update tracked model for consistency
            self.last_activity = datetime.now(timezone.utc)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to set model: {str(e)}"
            )

    async def interrupt(self):
        """
        Interrupt the current operation.

        Raises:
            HTTPException: If session not connected or SDK call fails
        """
        if not self.client or self.status != "connected":
            raise HTTPException(status_code=400, detail="Session not connected")

        try:
            await self.client.interrupt()
            self.last_activity = datetime.now(timezone.utc)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to interrupt: {str(e)}"
            )

    async def set_permission_mode(self, mode: str):
        """
        Change the permission mode for this session.

        Args:
            mode: Permission mode ("default", "acceptEdits", "plan", "bypassPermissions")

        Raises:
            HTTPException: If session not connected or SDK call fails
        """
        if not self.client or self.status != "connected":
            raise HTTPException(status_code=400, detail="Session not connected")

        try:
            await self.client.set_permission_mode(mode)
            self.last_activity = datetime.now(timezone.utc)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to set permission mode: {str(e)}"
            )

    async def get_server_info(self) -> dict[str, Any]:
        """
        Get server initialization info.

        Returns:
            Dictionary with server info (commands, output styles, etc.)

        Raises:
            HTTPException: If session not connected or info not available
        """
        if not self.client or self.status != "connected":
            raise HTTPException(status_code=400, detail="Session not connected")

        try:
            # Cache server info if not already cached
            if self.server_info is None:
                self.server_info = await self.client.get_server_info()

            if self.server_info is None:
                # Return empty dict if not available
                return {}

            return self.server_info
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get server info: {str(e)}"
            )

    def get_status(self) -> SessionStatus:
        """
        Get current session status.

        Returns:
            SessionStatus object
        """
        pending_perm = None
        if self.pending_permission:
            pending_perm = PermissionRequest(**self.pending_permission)

        return SessionStatus(
            session_id=self.session_id,
            status=self.status,
            pending_permission=pending_perm,
            current_model=self.current_model,
        )
