#!/usr/bin/env python3
"""
Shell CLI Client for Claude Agent API Server and AWS Bedrock AgentCore

Interactive shell client that connects to either:
1. Local API server via invocations API
2. AWS Bedrock AgentCore runtime

Usage:
    # Local API server mode
    python shell_client.py [--url URL] [--cwd CWD]

    # AgentCore mode (requires TOKEN environment variable)
    python shell_client.py --agentcore --agentcore-url https://your-agentcore-url/invocations
    python shell_client.py --agentcore --region us-west-2

Environment Variables (for AgentCore mode):
    TOKEN        - Bearer token for authentication
    AGENT_ARN    - Agent ARN for invocation (optional if --agentcore-url provided)
    AWS_REGION   - AWS region (optional, can use --region)

Examples:
    # Local mode
    python shell_client.py
    python shell_client.py --url http://localhost:8000

    # AgentCore mode with direct URL
    export TOKEN="your-token"
    python shell_client.py --agentcore --agentcore-url https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/your-arn/invocations

    # AgentCore mode with ARN (auto-constructs URL)
    export TOKEN="your-token"
    export AGENT_ARN="your-agent-arn"
    python shell_client.py --agentcore --region us-west-2
"""

import argparse
import sys
import json
import os
import urllib.parse
import uuid
from typing import Optional

import httpx


class ShellClient:
    """Interactive shell client using invocations API or AgentCore."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        initial_cwd: Optional[str] = None,
        agentcore_mode: bool = False,
        agentcore_url: Optional[str] = None,
        region: Optional[str] = None,
        agent_arn: Optional[str] = None,
        auth_token: Optional[str] = None
    ):
        self.agentcore_mode = agentcore_mode
        self.running = True

        if agentcore_mode:
            # AgentCore mode setup
            self.auth_token = auth_token or os.environ.get('TOKEN')
            if not self.auth_token:
                raise ValueError("TOKEN environment variable is required for AgentCore mode")

            # Use direct URL if provided, otherwise construct from ARN
            if agentcore_url:
                self.base_url = agentcore_url
                self.agent_arn = None
                self.region = None
            else:
                self.agent_arn = agent_arn or os.environ.get('AGENT_ARN')
                self.region = region or os.environ.get('AWS_REGION', 'us-west-2')

                if not self.agent_arn:
                    raise ValueError("AGENT_ARN environment variable or --agentcore-url is required for AgentCore mode")

                # Construct AgentCore URL from ARN
                escaped_agent_arn = urllib.parse.quote(self.agent_arn, safe='')
                self.base_url = f"https://bedrock-agentcore.{self.region}.amazonaws.com/runtimes/{escaped_agent_arn}/invocations?qualifier=DEFAULT"

            # Generate session ID with full UUID (36 chars) + prefix = 50 chars total
            self.session_id = f"shell-session-{uuid.uuid4()}"
            self.current_cwd = initial_cwd or "/workspace"
        else:
            # Local API server mode
            self.base_url = base_url or "http://127.0.0.1:8000"
            self.invocations_url = f"{self.base_url}/invocations"
            self.current_cwd = initial_cwd or self._get_initial_cwd()
            self.agent_arn = None
            self.auth_token = None
            self.session_id = None

    def _get_initial_cwd(self) -> str:
        """Get initial working directory from server (local mode only)."""
        if self.agentcore_mode:
            return "/workspace"

        try:
            with httpx.Client() as client:
                response = client.post(
                    self.invocations_url,
                    json={
                        "path": "/shell/cwd",
                        "method": "GET"
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("cwd", "/workspace")
        except Exception as e:
            print(f"Warning: Could not get initial cwd: {e}")
        return "/workspace"

    def execute_command_agentcore(self, command: str) -> None:
        """Execute command via AWS Bedrock AgentCore."""
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "X-Amzn-Trace-Id": f"shell-trace-{uuid.uuid4()}",
                "Content-Type": "application/json",
                "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": self.session_id
            }

            # Use the same invocations payload format as local mode
            payload = {
                "path": "/shell/execute",
                "method": "POST",
                "payload": {
                    "command": command,
                    "cwd": self.current_cwd
                }
            }

            with httpx.Client() as client:
                # Stream the response
                with client.stream(
                    "POST",
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=300.0
                ) as response:
                    if response.status_code != 200:
                        print(f"Error: {response.status_code}")
                        try:
                            error_data = response.json()
                            print(json.dumps(error_data, indent=2))
                        except:
                            print(response.text[:500])
                        return

                    # Stream output
                    for chunk in response.iter_bytes():
                        if chunk:
                            print(chunk.decode('utf-8', errors='replace'), end='', flush=True)

        except httpx.TimeoutException:
            print("\nError: Command execution timed out")
        except httpx.RequestError as e:
            print(f"\nError: Failed to execute command: {e}")
        except KeyboardInterrupt:
            print("\n^C")
        except Exception as e:
            print(f"\nError: {e}")

    def execute_command_local(self, command: str) -> None:
        """Execute command via local API server."""
        try:
            with httpx.Client() as client:
                # Stream the command execution
                with client.stream(
                    "POST",
                    self.invocations_url,
                    json={
                        "path": "/shell/execute",
                        "method": "POST",
                        "payload": {
                            "command": command,
                            "cwd": self.current_cwd
                        }
                    },
                    timeout=300.0
                ) as response:
                    if response.status_code != 200:
                        print(f"Error: {response.status_code} {response.reason_phrase}")
                        return

                    # Stream output line by line
                    for chunk in response.iter_bytes():
                        if chunk:
                            print(chunk.decode('utf-8', errors='replace'), end='', flush=True)

                # Update current directory if it was a cd command
                if command.strip().startswith('cd '):
                    self._update_cwd()

        except httpx.TimeoutException:
            print("\nError: Command execution timed out")
        except httpx.RequestError as e:
            print(f"\nError: Failed to execute command: {e}")
        except KeyboardInterrupt:
            print("\n^C")
        except Exception as e:
            print(f"\nError: {e}")

    def execute_command(self, command: str) -> None:
        """Execute a shell command."""
        if self.agentcore_mode:
            self.execute_command_agentcore(command)
        else:
            self.execute_command_local(command)

    def _update_cwd(self) -> None:
        """Update current working directory from server (local mode only)."""
        if self.agentcore_mode:
            return

        try:
            with httpx.Client() as client:
                response = client.post(
                    self.invocations_url,
                    json={
                        "path": "/shell/cwd",
                        "method": "GET"
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    self.current_cwd = data.get("cwd", self.current_cwd)
        except Exception as e:
            print(f"Warning: Could not update cwd: {e}")

    def run(self) -> None:
        """Run the interactive shell."""
        print("Shell CLI Client")
        if self.agentcore_mode:
            print(f"Mode: AWS Bedrock AgentCore")
            print(f"URL: {self.base_url}")
            if self.region:
                print(f"Region: {self.region}")
            print(f"Session ID: {self.session_id}")
        else:
            print(f"Mode: Local API Server")
            print(f"Connected to: {self.base_url}")
            print(f"Working directory: {self.current_cwd}")
        print("Type 'exit' or 'quit' to exit, Ctrl+C to interrupt command")
        print()

        while self.running:
            try:
                # Show prompt
                if self.agentcore_mode:
                    prompt = "\033[1;35mAgentCore\033[0m $ "
                else:
                    prompt = f"\033[1;36m{self.current_cwd}\033[0m $ "
                command = input(prompt).strip()

                # Handle empty command
                if not command:
                    continue

                # Handle exit commands
                if command.lower() in ['exit', 'quit']:
                    print("Goodbye!")
                    break

                # Execute command
                self.execute_command(command)

            except KeyboardInterrupt:
                print("\n^C")
                print("Type 'exit' or 'quit' to exit")
            except EOFError:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive shell client for Claude Agent API Server or AWS Bedrock AgentCore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables (for AgentCore mode):
  TOKEN        Bearer token for authentication
  AGENT_ARN    Agent ARN for invocation (optional if --agentcore-url provided)
  AWS_REGION   AWS region (can override with --region)

Examples:
  # Local API server
  python shell_client.py
  python shell_client.py --url http://localhost:8000

  # AWS Bedrock AgentCore with direct URL
  export TOKEN="your-token"
  python shell_client.py --agentcore --agentcore-url https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/your-arn/invocations

  # AWS Bedrock AgentCore with ARN (auto-constructs URL)
  export TOKEN="your-token"
  export AGENT_ARN="your-agent-arn"
  python shell_client.py --agentcore --region us-west-2
        """
    )

    # Mode selection
    parser.add_argument(
        "--agentcore",
        action="store_true",
        help="Use AWS Bedrock AgentCore mode (requires TOKEN and AGENT_ARN env vars)"
    )

    # Local mode options
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="Base URL of the API server (local mode, default: http://127.0.0.1:8000)"
    )
    parser.add_argument(
        "--cwd",
        help="Initial working directory (local mode)"
    )

    # AgentCore mode options
    parser.add_argument(
        "--agentcore-url",
        help="Direct URL for AgentCore invocations (if not provided, constructs from AGENT_ARN and region)"
    )
    parser.add_argument(
        "--region",
        help="AWS region for AgentCore (default: from AWS_REGION env or us-west-2)"
    )
    parser.add_argument(
        "--agent-arn",
        help="Agent ARN (default: from AGENT_ARN env variable)"
    )
    parser.add_argument(
        "--token",
        help="Auth token (default: from TOKEN env variable)"
    )

    args = parser.parse_args()

    try:
        if args.agentcore:
            # AgentCore mode
            client = ShellClient(
                agentcore_mode=True,
                agentcore_url=args.agentcore_url,
                region=args.region,
                agent_arn=args.agent_arn,
                auth_token=args.token,
                initial_cwd=args.cwd
            )
        else:
            # Local mode
            client = ShellClient(
                base_url=args.url,
                initial_cwd=args.cwd
            )

        client.run()

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
