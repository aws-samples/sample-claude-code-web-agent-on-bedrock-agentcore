#!/usr/bin/env python3
"""
Claude Agent API Client

A command-line client that communicates with the Claude Agent API Server.
Provides an interactive interface for multi-turn conversations with
Claude, including permission management and session control.

Features:
- Interactive command-line interface
- Session management (create, resume, list)
- Permission approval workflow
- Colored output for better readability
- Command shortcuts (exit, clear, sessions, help)
"""

import asyncio
import json
import sys
from typing import Optional

import httpx


class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    GRAY = "\033[90m"
    CYAN = "\033[96m"


class APIClient:
    """
    Client for communicating with the Claude Agent API Server.

    Handles all HTTP requests to the server and provides a simple
    interface for session and message management.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        """
        Initialize the API client.

        Args:
            base_url: Base URL of the API server
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 minute timeout

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def create_session(
        self,
        resume_session_id: Optional[str] = None,
        enable_proxy: bool = False,
        model: Optional[str] = None,
        background_model: Optional[str] = None,
        cwd: Optional[str] = None,
    ) -> dict:
        """
        Create a new session or resume an existing one.

        Args:
            resume_session_id: Optional session ID to resume
            enable_proxy: Enable LiteLLM proxy mode
            model: Model to use for the session
            background_model: Background model for agents
            cwd: Working directory for the session

        Returns:
            Session information dictionary

        Raises:
            Exception: If API request fails
        """
        payload = {"enable_proxy": enable_proxy}
        if resume_session_id:
            payload["resume_session_id"] = resume_session_id
        if model:
            payload["model"] = model
        if background_model:
            payload["background_model"] = background_model
        if cwd:
            payload["cwd"] = cwd

        response = await self.client.post(f"{self.base_url}/sessions", json=payload)
        response.raise_for_status()
        return response.json()

    async def list_sessions(self) -> dict:
        """
        List all active sessions on the server.

        Returns:
            Dictionary with list of sessions
        """
        response = await self.client.get(f"{self.base_url}/sessions")
        response.raise_for_status()
        return response.json()

    async def list_available_sessions(self) -> dict:
        """
        List all available sessions from disk.

        Returns:
            Dictionary with list of available sessions
        """
        response = await self.client.get(f"{self.base_url}/sessions/available")
        response.raise_for_status()
        return response.json()

    async def get_session_status(self, session_id: str) -> dict:
        """
        Get the status of a session.

        Args:
            session_id: The session ID

        Returns:
            Session status dictionary
        """
        response = await self.client.get(
            f"{self.base_url}/sessions/{session_id}/status"
        )
        response.raise_for_status()
        return response.json()

    async def send_message(self, session_id: str, message: str) -> dict:
        """
        Send a message in a session.

        Args:
            session_id: The session ID
            message: The message to send

        Returns:
            Response dictionary with assistant's reply
        """
        payload = {"message": message}
        response = await self.client.post(
            f"{self.base_url}/sessions/{session_id}/messages",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def respond_to_permission(
        self,
        session_id: str,
        request_id: str,
        allowed: bool,
        apply_suggestions: bool = False,
    ):
        """
        Respond to a permission request.

        Args:
            session_id: The session ID
            request_id: The permission request ID
            allowed: Whether to allow the operation
            apply_suggestions: Whether to apply suggestions
        """
        payload = {
            "request_id": request_id,
            "allowed": allowed,
            "apply_suggestions": apply_suggestions,
        }
        response = await self.client.post(
            f"{self.base_url}/sessions/{session_id}/permissions/respond",
            json=payload,
        )
        response.raise_for_status()

    async def set_model(self, session_id: str, model: Optional[str] = None):
        """
        Change the model for a session.

        Args:
            session_id: The session ID
            model: Model name (None for default)
        """
        payload = {"model": model}
        response = await self.client.post(
            f"{self.base_url}/sessions/{session_id}/model",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def interrupt(self, session_id: str):
        """
        Interrupt the current operation in a session.

        Args:
            session_id: The session ID
        """
        response = await self.client.post(
            f"{self.base_url}/sessions/{session_id}/interrupt"
        )
        response.raise_for_status()
        return response.json()

    async def set_permission_mode(self, session_id: str, mode: str):
        """
        Change the permission mode for a session.

        Args:
            session_id: The session ID
            mode: Permission mode (default, acceptEdits, plan, bypassPermissions)
        """
        payload = {"mode": mode}
        response = await self.client.post(
            f"{self.base_url}/sessions/{session_id}/permission_mode",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def get_server_info(self, session_id: str):
        """
        Get server initialization info for a session.

        Args:
            session_id: The session ID

        Returns:
            Dictionary with server info
        """
        response = await self.client.get(
            f"{self.base_url}/sessions/{session_id}/server_info"
        )
        response.raise_for_status()
        return response.json()

    async def close_session(self, session_id: str):
        """
        Close a session.

        Args:
            session_id: The session ID
        """
        response = await self.client.delete(f"{self.base_url}/sessions/{session_id}")
        response.raise_for_status()


class InteractiveClient:
    """
    Interactive command-line client for Claude Agent API.

    Provides a user-friendly interface with colored output, session
    management, and permission handling.
    """

    def __init__(
        self,
        api_client: APIClient,
        enable_proxy: bool = False,
        model: Optional[str] = None,
        background_model: Optional[str] = None,
        cwd: Optional[str] = None,
    ):
        """
        Initialize the interactive client.

        Args:
            api_client: The API client instance
            enable_proxy: Enable LiteLLM proxy mode
            model: Initial model to use for the session
            background_model: Background model for agents
            cwd: Working directory for the session
        """
        self.api_client = api_client
        self.current_session_id: Optional[str] = None
        self.permission_check_task: Optional[asyncio.Task] = None
        self.enable_proxy = enable_proxy
        self.background_model = background_model
        self.model = model
        self.cwd = cwd

    def print_welcome(self):
        """Print welcome banner and instructions."""
        print("\n" + "=" * 60)
        print("🎉 Welcome to Claude Agent Interactive Client!")
        print("=" * 60)
        print("\n📝 Instructions:")
        print("  • Type your questions or requests")
        print("  • Type 'exit' or 'quit' to exit")
        print("  • Type 'clear' to start a new session")
        print("  • Type 'sessions' to list and switch between sessions")
        print("  • Type 'model <name>' to change model (haiku/sonnet/default)")
        print("  • Type 'mode <name>' to change permission mode")
        print("  • Type 'interrupt' to stop current operation")
        print("  • Type 'info' to show server information")
        print("  • Type 'help' for more information")
        print("\n💡 Tip:")
        print("  • Read-only tools are automatically allowed")
        print("  • Write operations require your approval")
        print("=" * 60 + "\n")

    def print_help(self):
        """Print help information."""
        print("\n" + "=" * 60)
        print("📖 Help Information")
        print("=" * 60)
        print("\nAvailable Commands:")
        print("  exit/quit         - Exit the program")
        print("  clear             - Start a new session")
        print("  sessions          - List and switch between sessions")
        print("  model <name>      - Change model (haiku/sonnet/default)")
        print(
            "  mode <name>       - Change permission mode (default/acceptEdits/plan/bypassPermissions)"
        )
        print("  interrupt         - Stop current operation")
        print("  info              - Show server information")
        print("  help              - Show this help message")
        print("\nAvailable Tools:")
        print("  📄 Read    - Read file contents (auto-approved)")
        print("  🔍 Glob    - Find files (auto-approved)")
        print("  🔎 Grep    - Search content (auto-approved)")
        print("  ✏️ Write   - Write files (requires approval)")
        print("  ✂️ Edit    - Edit files (requires approval)")
        print("  💻 Bash    - Run commands (requires approval)")
        print("\nExample Questions:")
        print('  • "Create a hello.py file"')
        print('  • "Read the README.md file"')
        print('  • "Run ls -la command"')
        print('  • "Calculate 123 * 456 using Python"')
        print("=" * 60 + "\n")

    async def display_available_sessions(self) -> list:
        """
        Display all available sessions and return the list.

        Returns:
            List of session dictionaries
        """
        try:
            result = await self.api_client.list_available_sessions()
            sessions = result.get("sessions", [])

            if not sessions:
                print(f"\n{Colors.GRAY}📭 No saved sessions found{Colors.RESET}\n")
                return []

            print("\n" + "=" * 60)
            print("📚 Available Sessions")
            print("=" * 60)

            for i, session in enumerate(sessions[:10], 1):  # Show top 10
                session_id = session["session_id"]
                modified = session["modified"]
                preview = session["preview"]

                print(f"\n{i}. {session_id[:40]}...")
                print(f"   Time: {modified}")
                print(f"   Preview: {preview}...")

            print("\n" + "=" * 60 + "\n")
            return sessions

        except Exception as e:
            print(f"{Colors.RED}❌ Error listing sessions: {e}{Colors.RESET}")
            return []

    async def choose_session(self) -> Optional[str]:
        """
        Let user choose a session to resume.

        Returns:
            Session ID to resume, None for new session, or "quit" to exit
        """
        sessions = await self.display_available_sessions()

        if not sessions:
            print("💡 Starting new session...")
            return None

        print("Please choose:")
        print(f"  Enter number (1-{min(10, len(sessions))}) - Resume that session")
        print("  Enter 'new' or press Enter - Start new session")
        print("  Enter 'quit' - Exit program\n")

        choice = input("Your choice: ").strip().lower()

        if choice == "quit":
            return "quit"
        elif choice == "" or choice == "new":
            return None
        else:
            try:
                index = int(choice) - 1
                if 0 <= index < len(sessions):
                    selected = sessions[index]
                    print(
                        f"\n✅ Will resume session: {selected['session_id'][:40]}...\n"
                    )
                    return selected["session_id"]
                else:
                    print(
                        f"\n{Colors.YELLOW}⚠️ Invalid choice, starting new session{Colors.RESET}\n"
                    )
                    return None
            except ValueError:
                print(
                    f"\n{Colors.YELLOW}⚠️ Invalid input, starting new session{Colors.RESET}\n"
                )
                return None

    async def check_permission_requests(self):
        """
        Background task to check for pending permission requests.

        This task polls the server for pending permissions and prompts
        the user to approve or deny them.
        """
        while True:
            try:
                if not self.current_session_id:
                    await asyncio.sleep(1)
                    continue

                # Check session status
                status = await self.api_client.get_session_status(
                    self.current_session_id
                )

                pending = status.get("pending_permission")
                if pending:
                    await self.handle_permission_request(pending)

                await asyncio.sleep(0.5)  # Poll every 500ms

            except asyncio.CancelledError:
                break
            except Exception:
                # Ignore errors in background task
                await asyncio.sleep(1)

    async def handle_permission_request(self, permission: dict):
        """
        Handle a permission request interactively.

        Args:
            permission: Permission request dictionary
        """
        request_id = permission["request_id"]
        tool_name = permission["tool_name"]
        tool_input = permission["tool_input"]
        suggestions = permission.get("suggestions", [])

        print(f"\n{Colors.YELLOW}⚠️  Permission Request{Colors.RESET}")
        print(f"{Colors.YELLOW}Tool: {tool_name}{Colors.RESET}")

        # Show tool-specific information
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            print(f"{Colors.YELLOW}Command: {command}{Colors.RESET}")

            # Check for dangerous patterns
            dangerous = ["rm -rf", "sudo", "chmod 777", "> /dev/", "dd if="]
            for pattern in dangerous:
                if pattern in command:
                    print(
                        f"{Colors.RED}🚨 Warning: Detected dangerous pattern: {pattern}{Colors.RESET}"
                    )

        elif tool_name in ["Write", "Edit"]:
            file_path = tool_input.get("file_path", "")
            print(f"{Colors.YELLOW}File: {file_path}{Colors.RESET}")

            # Check for system directories
            system_dirs = ["/etc/", "/usr/", "/bin/", "/sbin/", "/System/"]
            for sys_dir in system_dirs:
                if file_path.startswith(sys_dir):
                    print(
                        f"{Colors.RED}🚨 Warning: Attempting to modify system directory{Colors.RESET}"
                    )

        # Show suggestions
        has_suggestions = len(suggestions) > 0
        if has_suggestions:
            print(
                f"{Colors.GRAY}💡 System has {len(suggestions)} suggestion(s){Colors.RESET}"
            )
            for suggestion in suggestions:
                if suggestion.get("type") == "setMode":
                    mode = suggestion.get("mode")
                    dest = suggestion.get("destination", "session")
                    print(
                        f"{Colors.GRAY}  → Suggests switching to '{mode}' mode (scope: {dest}){Colors.RESET}"
                    )

        # Ask user
        if has_suggestions:
            prompt = f"{Colors.YELLOW}Allow? [Y/n/a(apply suggestions)/d(details)]: {Colors.RESET}"
        else:
            prompt = f"{Colors.YELLOW}Allow? [Y/n/d(details)]: {Colors.RESET}"

        while True:
            choice = input(prompt).strip().lower()

            if choice == "d":
                # Show details
                print(f"\n{Colors.CYAN}Details:{Colors.RESET}")
                print(f"  Tool: {tool_name}")
                print(f"  Input: {json.dumps(tool_input, indent=4)}")
                if suggestions:
                    print(f"  Suggestions: {json.dumps(suggestions, indent=4)}")
                print()
                continue

            elif choice in ["y", "yes", ""]:
                print(f"{Colors.GREEN}✅ Approved{Colors.RESET}")
                await self.api_client.respond_to_permission(
                    self.current_session_id, request_id, allowed=True
                )
                break

            elif choice == "a" and has_suggestions:
                print(
                    f"{Colors.GREEN}✅ Applying {len(suggestions)} suggestion(s){Colors.RESET}"
                )
                await self.api_client.respond_to_permission(
                    self.current_session_id,
                    request_id,
                    allowed=True,
                    apply_suggestions=True,
                )
                break

            elif choice in ["n", "no"]:
                print(f"{Colors.RED}❌ Denied{Colors.RESET}")
                await self.api_client.respond_to_permission(
                    self.current_session_id, request_id, allowed=False
                )
                break

            else:
                print(f"{Colors.RED}Invalid choice. Please enter Y/n/d{Colors.RESET}")

    async def run(self):
        """Run the interactive client main loop."""
        self.print_welcome()

        # Choose session
        session_choice = await self.choose_session()

        if session_choice == "quit":
            print("👋 Goodbye!")
            return

        # Create/resume session
        try:
            print("🔄 Connecting to server...")
            session_info = await self.api_client.create_session(
                resume_session_id=session_choice,
                enable_proxy=self.enable_proxy,
                model=self.model,
                background_model=self.background_model,
                cwd=self.cwd,
            )
            self.current_session_id = session_info["session_id"]

            if session_choice:
                print("✅ Resumed session\n")
            else:
                status_msg = "✅ Connected to Claude Agent"
                if self.enable_proxy:
                    status_msg += " (Proxy Mode)"
                if self.model:
                    status_msg += f" [Main: {self.model}]"
                if self.background_model:
                    status_msg += f" [Background: {self.background_model}]"
                print(status_msg + "\n")

        except Exception as e:
            print(f"{Colors.RED}❌ Failed to connect: {e}{Colors.RESET}")
            return

        # Start permission checking task
        self.permission_check_task = asyncio.create_task(
            self.check_permission_requests()
        )

        # Main interaction loop
        try:
            while True:
                try:
                    # Get user input
                    user_input = input(f"{Colors.GREEN}👤 You: {Colors.RESET}").strip()

                    # Handle special commands
                    if user_input.lower() in ["exit", "quit"]:
                        print("\n👋 Goodbye!")
                        break

                    if user_input.lower() == "clear":
                        print("\n🔄 Starting new session...\n")
                        # Close old session
                        await self.api_client.close_session(self.current_session_id)
                        # Create new session
                        session_info = await self.api_client.create_session(
                            enable_proxy=self.enable_proxy,
                            model=self.model,
                            background_model=self.background_model,
                            cwd=self.cwd,
                        )
                        self.current_session_id = session_info["session_id"]
                        print("✅ New session started\n")
                        continue

                    if user_input.lower() == "help":
                        self.print_help()
                        continue

                    if user_input.lower() == "sessions":
                        # Display sessions and allow switching
                        sessions = await self.display_available_sessions()
                        if sessions:
                            print("💡 Options:")
                            print(
                                f"  Enter number (1-{min(10, len(sessions))}) - Switch to that session"
                            )
                            print("  Press Enter - Continue with current session\n")

                            choice = input("Your choice: ").strip()

                            if choice:
                                try:
                                    index = int(choice) - 1
                                    if 0 <= index < len(sessions):
                                        selected_session_id = sessions[index][
                                            "session_id"
                                        ]
                                        print(
                                            f"\n🔄 Switching to session: {selected_session_id[:40]}...\n"
                                        )

                                        # Close current session
                                        await self.api_client.close_session(
                                            self.current_session_id
                                        )

                                        # Resume selected session
                                        session_info = (
                                            await self.api_client.create_session(
                                                resume_session_id=selected_session_id,
                                                enable_proxy=self.enable_proxy,
                                                model=self.model,
                                                background_model=self.background_model,
                                                cwd=self.cwd,
                                            )
                                        )
                                        self.current_session_id = session_info[
                                            "session_id"
                                        ]
                                        print("✅ Session switched\n")
                                    else:
                                        print(
                                            f"\n{Colors.YELLOW}⚠️ Invalid choice{Colors.RESET}\n"
                                        )
                                except ValueError:
                                    print(
                                        f"\n{Colors.YELLOW}⚠️ Invalid input{Colors.RESET}\n"
                                    )
                        continue

                    if user_input.lower().startswith("model "):
                        # Change model: "model haiku" or "model default"
                        model_name = user_input[6:].strip()
                        if model_name.lower() == "default":
                            model_name = None
                        elif model_name.lower() == "haiku":
                            model_name = "claude-3-5-haiku-20241022"
                        elif model_name.lower() == "sonnet":
                            model_name = "claude-3-5-sonnet-20241022"

                        try:
                            result = await self.api_client.set_model(
                                self.current_session_id, model_name
                            )
                            model_display = model_name or "default"
                            print(
                                f"{Colors.GREEN}✅ Model changed to: {model_display}{Colors.RESET}\n"
                            )
                        except Exception as e:
                            print(
                                f"{Colors.RED}❌ Failed to change model: {e}{Colors.RESET}\n"
                            )
                        continue

                    if user_input.lower() == "interrupt":
                        # Interrupt current operation
                        try:
                            await self.api_client.interrupt(self.current_session_id)
                            print(
                                f"{Colors.YELLOW}⚠️ Interrupt signal sent{Colors.RESET}\n"
                            )
                        except Exception as e:
                            print(
                                f"{Colors.RED}❌ Failed to interrupt: {e}{Colors.RESET}\n"
                            )
                        continue

                    if user_input.lower().startswith("mode "):
                        # Change permission mode: "mode default" or "mode acceptEdits"
                        mode_name = user_input[5:].strip()
                        try:
                            result = await self.api_client.set_permission_mode(
                                self.current_session_id, mode_name
                            )
                            print(
                                f"{Colors.GREEN}✅ Permission mode changed to: {mode_name}{Colors.RESET}\n"
                            )
                        except Exception as e:
                            print(
                                f"{Colors.RED}❌ Failed to change permission mode: {e}{Colors.RESET}\n"
                            )
                        continue

                    if user_input.lower() == "info":
                        # Get server info
                        try:
                            info = await self.api_client.get_server_info(
                                self.current_session_id
                            )
                            print(
                                f"\n{Colors.CYAN}📋 Server Information:{Colors.RESET}"
                            )
                            if info:
                                # Pretty print the info
                                import json

                                print(json.dumps(info, indent=2, ensure_ascii=False))
                            else:
                                print("  No server info available")
                            print()
                        except Exception as e:
                            print(
                                f"{Colors.RED}❌ Failed to get server info: {e}{Colors.RESET}\n"
                            )
                        continue

                    if not user_input:
                        continue

                    # Send message
                    response = await self.api_client.send_message(
                        self.current_session_id, user_input
                    )

                    # Display response
                    for msg_block in response["messages"]:
                        if msg_block["type"] == "text":
                            print(
                                f"{Colors.BLUE}🤖 Claude: {msg_block['content']}{Colors.RESET}"
                            )
                        elif msg_block["type"] == "tool_use":
                            tool_name = msg_block["tool_name"]
                            print(
                                f"{Colors.YELLOW}🔧 Using tool: {tool_name}{Colors.RESET}"
                            )

                    # Show cost if available
                    if response.get("cost_usd"):
                        print(
                            f"{Colors.GRAY}💰 Cost: ${response['cost_usd']:.6f}{Colors.RESET}"
                        )

                    print()  # Blank line

                except KeyboardInterrupt:
                    print("\n\n👋 Detected Ctrl+C, exiting...")
                    break

                except Exception as e:
                    print(f"\n{Colors.RED}❌ Error: {e}{Colors.RESET}")
                    print("Please try again or type 'exit' to quit\n")

        finally:
            # Cleanup
            if self.permission_check_task:
                self.permission_check_task.cancel()
                try:
                    await self.permission_check_task
                except asyncio.CancelledError:
                    pass

            if self.current_session_id:
                try:
                    await self.api_client.close_session(self.current_session_id)
                    print("✅ Session closed")
                except Exception:
                    pass


async def main():
    """Main entry point."""
    if "--help" in sys.argv or "-h" in sys.argv:
        print(
            """
Claude Agent Interactive Client

Usage:
    python client.py [--server SERVER_URL] [--proxy] [--model MODEL] [--background-model MODEL] [--cwd PATH]

Options:
    --server URL              API server URL (default: http://127.0.0.1:8000)
    --proxy                   Enable LiteLLM proxy mode
    --model MODEL             Main model to use (e.g., claude-3-5-sonnet-20241022, gpt-4)
    --background-model MODEL  Background model for agents (e.g., claude-3-5-haiku-20241022, gpt-3.5-turbo)
    --cwd PATH                Working directory for the session (e.g., /workspace)
    -h, --help                Show this help message

Description:
    Interactive command-line client for Claude Agent API Server.
    Supports multi-turn conversations, session management, and
    permission control for tool usage.

    When --proxy is enabled, the SDK will route requests through
    the server's /v1/messages endpoint, allowing use of alternative
    LLM providers via LiteLLM.

    The --model parameter sets the main model for user interactions.
    The --background-model parameter sets the model for background agents.
    The --cwd parameter sets the working directory for the session.

Examples:
    python client.py
    python client.py --server http://localhost:8000
    python client.py --proxy --model gpt-4 --background-model gpt-3.5-turbo
    python client.py --model claude-3-5-sonnet-20241022 --background-model claude-3-5-haiku-20241022
    python client.py --cwd /workspace
        """
        )
        sys.exit(0)

    # Parse server URL
    server_url = "http://127.0.0.1:8000"
    if "--server" in sys.argv:
        idx = sys.argv.index("--server")
        if idx + 1 < len(sys.argv):
            server_url = sys.argv[idx + 1]

    # Parse proxy flag
    enable_proxy = "--proxy" in sys.argv

    # Parse model
    model = None
    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        if idx + 1 < len(sys.argv):
            model = sys.argv[idx + 1]

    # Parse background model
    background_model = None
    if "--background-model" in sys.argv:
        idx = sys.argv.index("--background-model")
        if idx + 1 < len(sys.argv):
            background_model = sys.argv[idx + 1]

    # Parse cwd
    cwd = None
    if "--cwd" in sys.argv:
        idx = sys.argv.index("--cwd")
        if idx + 1 < len(sys.argv):
            cwd = sys.argv[idx + 1]

    # Create client
    api_client = APIClient(base_url=server_url)

    try:
        # Check server health
        response = await api_client.client.get(f"{server_url}/health")
        if response.status_code != 200:
            print(f"{Colors.RED}❌ Server is not healthy{Colors.RESET}")
            return
    except Exception as e:
        print(f"{Colors.RED}❌ Cannot connect to server at {server_url}{Colors.RESET}")
        print(f"{Colors.RED}   Error: {e}{Colors.RESET}")
        print(f"\n{Colors.YELLOW}💡 Make sure the server is running:{Colors.RESET}")
        print(f"{Colors.YELLOW}   python api_server/server.py{Colors.RESET}\n")
        return

    # Run interactive client
    interactive_client = InteractiveClient(
        api_client,
        enable_proxy=enable_proxy,
        model=model,
        background_model=background_model,
        cwd=cwd,
    )
    try:
        await interactive_client.run()
    finally:
        await api_client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Program exited")
        sys.exit(0)
