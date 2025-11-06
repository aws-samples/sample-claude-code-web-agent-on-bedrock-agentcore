"""
Unified Invocation Endpoint.

Provides a single entry point for all API operations, routing requests
based on the path and payload parameters.
"""

import os
import jwt
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request

from ..models import (
    CreateSessionRequest,
    PermissionResponse,
    SendMessageRequest,
    SetModelRequest,
    SetPermissionModeRequest,
)
from .messages import (
    get_session_status,
    interrupt_session,
    send_message,
    set_model,
    set_permission_mode,
)
from .permissions import respond_to_permission
from .files import get_file_info, list_files, save_file, SaveFileRequest
from .shell import execute_command, get_current_directory, set_current_directory, ShellExecuteRequest
from .terminal import (
    create_session as create_terminal_session,
    get_session_output,
    send_input,
    resize_session,
    close_session as close_terminal_session,
    get_session_status as get_terminal_status,
    list_sessions as list_terminal_sessions,
    stream_session_output,
    CreateSessionRequest as TerminalCreateRequest,
    InputRequest,
    ResizeRequest
)
from .sessions import (
    close_session,
    create_session,
    get_server_info,
    get_session_history,
    list_available_sessions,
    list_sessions,
)
from .oauth import get_github_oauth_token

router = APIRouter()


def parse_session_and_user_from_headers(request: Request) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse agentcore_session_id, user_id, and project_name from request headers.

    AgentCore Session ID format: user_id@workspace/project_name
    - user_id@workspace: default workspace, no specific project
    - user_id@workspace/my-project: specific project within workspace

    Args:
        request: FastAPI Request object

    Returns:
        Tuple of (agentcore_session_id, user_id, project_name)
    """
    agentcore_session_id = None
    user_id = None
    project_name = None

    # Extract agentcore_session_id from X-Amzn-Bedrock-AgentCore-Runtime-Session-Id header
    # FastAPI headers are case-insensitive, but we try common variations
    agentcore_session_id = request.headers.get("x-amzn-bedrock-agentcore-runtime-session-id")

    # Parse project_name from agentcore_session_id if present
    # Format: user_id@workspace/project_name
    if agentcore_session_id:
        if "@workspace/" in agentcore_session_id:
            # Has project: user_id@workspace/project_name
            parts = agentcore_session_id.split("@workspace/", 1)
            if len(parts) == 2:
                project_name = parts[1]
        # user_id will be extracted from JWT below

    # Extract and decode JWT token from Authorization header (case-insensitive)
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()  # Remove "Bearer " prefix and whitespace
        try:
            # Decode JWT without verification (for extracting sub claim)
            # In production, you should verify the token signature
            decoded = jwt.decode(token, options={"verify_signature": False})
            user_id = decoded.get("sub")
        except jwt.DecodeError:
            # Token decode failed, user_id remains None
            pass
        except Exception:
            # Any other error, user_id remains None
            pass

    return agentcore_session_id, user_id, project_name


@router.post("/invocations")
async def invocations(http_request: Request, request: dict[str, Any]):
    """
    Unified invocation endpoint that routes to other API endpoints.

    This endpoint provides a single entry point for all API operations,
    routing requests based on the path and payload parameters.

    Args:
        request: Dictionary containing:
            - path: The API path to invoke (e.g., "/sessions", "/sessions/{id}/messages")
            - method: HTTP method (GET, POST, DELETE) - optional, defaults to POST
            - payload: The request payload (optional)
            - path_params: Path parameters as dict (optional, e.g., {"session_id": "abc"})

    Returns:
        The response from the invoked endpoint

    Examples:
        Create session:
        {
            "path": "/sessions",
            "method": "POST",
            "payload": {"resume_session_id": "optional-id"}
        }

        Send message:
        {
            "path": "/sessions/{session_id}/messages",
            "method": "POST",
            "path_params": {"session_id": "abc123"},
            "payload": {"message": "Hello"}
        }

        Get status:
        {
            "path": "/sessions/{session_id}/status",
            "method": "GET",
            "path_params": {"session_id": "abc123"}
        }
    """
    # Parse agentcore_session_id, user_id, and project_name from headers
    agentcore_session_id, user_id, project_name = parse_session_and_user_from_headers(http_request)

    # Ensure user's .claude directory is synced from S3 (first time only)
    if user_id:
        from ..server import claude_sync_manager
        if claude_sync_manager:
            try:
                print(f"🔄 Attempting initial sync for user: {user_id}")
                sync_result = await claude_sync_manager.ensure_initial_sync(user_id)
                print(f"📊 Sync result for user {user_id}: {sync_result.get('status')} - {sync_result.get('message', 'No message')}")
                if sync_result.get("status") == "error":
                    print(f"⚠️  Warning: Failed to sync .claude for user {user_id}: {sync_result.get('message')}")
            except Exception as e:
                # Log error but don't fail the request
                print(f"⚠️  Warning: Exception during .claude sync for user {user_id}: {e}")
        else:
            print(f"⚠️  Claude sync manager not initialized, skipping sync for user {user_id}")

    # Ensure project directory is synced from S3 (first time only)
    if user_id and project_name:
        from ..core.workspace_sync import sync_project_from_s3, backup_project_to_s3
        try:
            print(f"📁 Attempting project sync for user {user_id}, project: {project_name}")
            project_result = await sync_project_from_s3(
                user_id=user_id,
                project_name=project_name,
                bucket_name=os.environ.get("S3_WORKSPACE_BUCKET", ""),
                s3_prefix=os.environ.get("S3_WORKSPACE_PREFIX", "user_data"),
            )
            print(f"📊 Project sync result: {project_result.get('status')} - {project_result.get('message', 'No message')}")

            # If S3 had no data, try to backup local project to S3
            if project_result.get("status") == "skipped":
                s3_path = project_result.get("s3_path", "")
                print(
                    f"⏭️  No S3 data found for project {project_name}\n"
                    f"   📍 S3 Path: {s3_path}\n"
                    f"   Checking for local project data to backup"
                )

                # Try to backup local project to S3
                backup_result = await backup_project_to_s3(
                    user_id=user_id,
                    project_name=project_name,
                    bucket_name=os.environ.get("S3_WORKSPACE_BUCKET", ""),
                    s3_prefix=os.environ.get("S3_WORKSPACE_PREFIX", "user_data"),
                )

                if backup_result.get("status") == "success":
                    s3_path = backup_result.get("s3_path", "")
                    print(
                        f"✅ Initial project backup completed: "
                        f"{backup_result.get('files_synced', 0)} files backed up\n"
                        f"   📍 S3 Path: {s3_path}"
                    )
                elif backup_result.get("status") == "skipped":
                    local_path = backup_result.get("local_path", "")
                    print(
                        f"⏭️  No local project data to backup for {project_name}\n"
                        f"   📂 Local Path: {local_path}"
                    )

        except Exception as e:
            print(f"⚠️  Warning: Exception during project sync: {e}")

    path = request.get("path")
    method = request.get("method", "POST").upper()
    payload = request.get("payload", {})
    path_params = request.get("path_params", {})

    if not path:
        raise HTTPException(status_code=400, detail="Missing 'path' parameter")

    # Replace path parameters
    resolved_path = path
    for key, value in path_params.items():
        resolved_path = resolved_path.replace(f"{{{key}}}", str(value))

    # Log the invocation with agentcore session ID prominently
    if agentcore_session_id:
        print(f"🔀 Invocation → {method} {resolved_path}")
        print(f"   🆔 AgentCore Session ID: {agentcore_session_id}")
        if user_id:
            print(f"   👤 User ID: {user_id}")
        session_id_from_path = path_params.get("session_id")
        if session_id_from_path:
            print(f"   📋 Path Session ID: {session_id_from_path}")
    else:
        # Fallback when no agentcore session ID
        log_parts = [f"🔀 Invocation → {method} {resolved_path}"]
        if user_id:
            log_parts.append(f"user_id={user_id}")
        session_id_from_path = path_params.get("session_id")
        if session_id_from_path:
            log_parts.append(f"session_id={session_id_from_path}")
        print(" | ".join(log_parts))

    # Route to appropriate endpoint based on path and method
    try:
        if path == "/sessions" and method == "POST":
            # Create session
            req = CreateSessionRequest(**payload)
            return await create_session(req)

        elif path == "/sessions" and method == "GET":
            # List sessions
            cwd = payload.get("cwd") if payload else None
            return await list_sessions(cwd)

        elif path == "/sessions/available" and method == "GET":
            # List available sessions
            cwd = payload.get("cwd") if payload else None
            return await list_available_sessions(cwd)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/status")
            and method == "GET"
        ):
            # Get session status
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            return await get_session_status(session_id)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/messages/stream")
            and method == "POST"
        ):
            # Send message with streaming
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            req = SendMessageRequest(**payload)
            from .messages import send_message_stream
            return await send_message_stream(session_id, req)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/messages")
            and method == "POST"
        ):
            # Send message
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            req = SendMessageRequest(**payload)
            return await send_message(session_id, req)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/permissions/respond")
            and method == "POST"
        ):
            # Respond to permission
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            resp = PermissionResponse(**payload)
            return await respond_to_permission(session_id, resp)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/model")
            and method == "POST"
        ):
            # Set model
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            req = SetModelRequest(**payload)
            return await set_model(session_id, req)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/interrupt")
            and method == "POST"
        ):
            # Interrupt session
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            return await interrupt_session(session_id)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/permission_mode")
            and method == "POST"
        ):
            # Set permission mode
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            req = SetPermissionModeRequest(**payload)
            return await set_permission_mode(session_id, req)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/server_info")
            and method == "GET"
        ):
            # Get server info
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            return await get_server_info(session_id)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/history")
            and method == "GET"
        ):
            # Get session history
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            cwd = payload.get("cwd") if payload else None
            return await get_session_history(session_id, cwd)

        elif path.startswith("/sessions/") and method == "DELETE":
            # Close session
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            return await close_session(session_id)

        elif path == "/files" and method == "GET":
            # List files
            file_path = payload.get("path", ".")
            return await list_files(path=file_path)

        elif path == "/files/info" and method == "GET":
            # Get file info
            file_path = payload.get("path")
            if not file_path:
                raise HTTPException(status_code=400, detail="Missing 'path' in payload")
            return await get_file_info(path=file_path)

        elif path == "/files/save" and method == "POST":
            # Save file
            req = SaveFileRequest(**payload)
            return await save_file(req)

        elif path == "/shell/execute" and method == "POST":
            # Execute shell command (returns streaming response)
            req = ShellExecuteRequest(**payload)
            return await execute_command(req)

        elif path == "/shell/cwd" and method == "GET":
            # Get current working directory
            return await get_current_directory()

        elif path == "/shell/cwd" and method == "POST":
            # Set current working directory
            cwd = payload.get("cwd")
            if not cwd:
                raise HTTPException(status_code=400, detail="Missing 'cwd' in payload")
            return await set_current_directory(cwd)

        elif path == "/terminal/sessions" and method == "POST":
            # Create terminal session
            req = TerminalCreateRequest(**payload)
            return await create_terminal_session(req)

        elif path == "/terminal/sessions" and method == "GET":
            # List terminal sessions
            return await list_terminal_sessions()

        elif (
            path.startswith("/terminal/sessions/")
            and path.endswith("/stream")
            and method == "GET"
        ):
            # Stream terminal output (SSE)
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            return await stream_session_output(session_id)

        elif (
            path.startswith("/terminal/sessions/")
            and "/output" in path
            and method == "GET"
        ):
            # Get terminal output
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            seq = payload.get("seq", 0) if payload else 0
            return await get_session_output(session_id, seq)

        elif (
            path.startswith("/terminal/sessions/")
            and path.endswith("/input")
            and method == "POST"
        ):
            # Send terminal input
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            req = InputRequest(**payload)
            return await send_input(session_id, req)

        elif (
            path.startswith("/terminal/sessions/")
            and path.endswith("/resize")
            and method == "POST"
        ):
            # Resize terminal
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            req = ResizeRequest(**payload)
            return await resize_session(session_id, req)

        elif (
            path.startswith("/terminal/sessions/")
            and path.endswith("/status")
            and method == "GET"
        ):
            # Get terminal status
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            return await get_terminal_status(session_id)

        elif (
            path.startswith("/terminal/sessions/")
            and not path.endswith("/input")
            and not path.endswith("/resize")
            and not path.endswith("/status")
            and "/output" not in path
            and method == "DELETE"
        ):
            # Close terminal session
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            return await close_terminal_session(session_id)

        elif path == "/workspace/projects/backup" and method == "POST":
            # Backup project to S3
            from .workspace import backup_project, CreateProjectRequest
            req = CreateProjectRequest(**payload)
            return await backup_project(req)

        elif path == "/workspace/projects" and method == "POST":
            # Create project
            from .workspace import create_project, CreateProjectRequest
            req = CreateProjectRequest(**payload)
            return await create_project(req)

        elif path.startswith("/workspace/projects/") and method == "GET":
            # List projects for user
            from .workspace import list_projects
            user_id = path_params.get("user_id")
            if not user_id:
                raise HTTPException(
                    status_code=400, detail="Missing user_id in path_params"
                )
            return await list_projects(user_id)

        elif path == "/oauth/github/token" and method == "POST":
            # Get GitHub OAuth token
            return await get_github_oauth_token(http_request)

        elif path == "/oauth/github/callback" and method == "GET":
            # GitHub OAuth callback (3LO flow completion)
            from .oauth import github_oauth_callback

            # Extract session_id from query_params in request payload
            query_params = request.get("query_params", {})
            session_id = query_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400,
                    detail="Missing session_id query parameter"
                )
            return await github_oauth_callback(http_request, session_id)

        elif path == "/agentcore/session/stop" and method == "POST":
            # Stop AgentCore runtime session
            from .agentcore import stop_agentcore_session

            # Extract qualifier from query_params if provided
            query_params = request.get("query_params", {})
            qualifier = query_params.get("qualifier", "DEFAULT")
            return await stop_agentcore_session(http_request, qualifier)

        elif path == "/github/repositories" and method == "GET":
            # List GitHub repositories
            from .oauth import list_github_repositories
            return await list_github_repositories()

        elif path == "/github/create-project" and method == "POST":
            # Create project from GitHub repository
            from .oauth import create_project_from_github
            # Extract params - try both path_params and query_params for compatibility
            params = request.get("path_params", {}) or request.get("query_params", {})
            user_id = params.get("user_id")
            repository_url = params.get("repository_url")
            project_name = params.get("project_name")
            branch = params.get("branch")

            if not user_id or not repository_url:
                raise HTTPException(
                    status_code=400,
                    detail="Missing required parameters: user_id and repository_url"
                )

            return await create_project_from_github(
                user_id=user_id,
                repository_url=repository_url,
                project_name=project_name,
                branch=branch
            )

        elif path == "/health" and method == "GET":
            # Health check - import here to avoid circular dependency
            from ..server import health_check

            return await health_check()

        elif path == "/ping" and method == "GET":
            # Ping endpoint - import here to avoid circular dependency
            from ..server import ping

            return await ping()

        else:
            error_msg = f"Unknown path or method: {method} {path}"
            print(f"❌ Invocation Error (404): {error_msg} | path_params={path_params} | payload_keys={list(payload.keys()) if payload else []}")
            raise HTTPException(
                status_code=404,
                detail=error_msg,
            )

    except HTTPException as e:
        # Log HTTPException details
        if e.status_code == 404:
            print(f"❌ Invocation HTTPException (404): {e.detail}")
        elif e.status_code >= 400:
            print(f"❌ Invocation HTTPException ({e.status_code}): {e.detail}")
        raise
    except Exception as e:
        error_detail = f"Invocation error: {str(e)}"
        print(f"❌ Invocation Exception (500): {error_detail} | path={path} | method={method}")
        raise HTTPException(status_code=500, detail=error_detail)
