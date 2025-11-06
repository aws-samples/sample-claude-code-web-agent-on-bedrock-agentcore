# CLI Clients

This directory contains CLI clients for interacting with the Claude Agent API Server.

## Available Clients

### 1. AgentClient (`client.py`)

Full-featured Python client for the Claude Agent SDK API.

**Features:**
- Session management (create, resume, close)
- Message sending and receiving
- Permission handling
- Async/await support
- Direct and Invocations API modes

**Usage:**
```python
from cli_client import AgentClient

client = AgentClient(base_url="http://127.0.0.1:8000")
session = await client.create_session()
response = await client.send_message(session["session_id"], "Hello!")
```

### 2. Shell Client (`shell_client.py`)

Interactive shell terminal client with dual-mode support:
- **Local Mode**: Connect to local API server via invocations API
- **AgentCore Mode**: Connect to AWS Bedrock AgentCore runtime

**Features:**
- Interactive command-line shell
- Streaming command output (real-time display)
- Working directory management (local mode)
- cd command support (local mode)
- AWS Bedrock AgentCore integration
- httpx for HTTP streaming
- Bearer token authentication (AgentCore)
- Session management with unique IDs

**Usage:**

**Local Mode:**
```bash
# Basic usage (local server)
python cli_client/shell_client.py

# Specify server URL
python cli_client/shell_client.py --url http://localhost:8000

# Set initial working directory
python cli_client/shell_client.py --cwd /workspace
```

**AgentCore Mode:**
```bash
# Set environment variables
export TOKEN="your-bearer-token"
export AGENT_ARN="your-agent-arn"
export AWS_REGION="us-west-2"  # Optional, defaults to us-west-2

# Run in AgentCore mode
python cli_client/shell_client.py --agentcore

# Or specify region via command line
python cli_client/shell_client.py --agentcore --region us-east-1

# Use the test script
./test_agentcore_shell.sh
```

**Commands:**
- Type any shell command and press Enter
- `cd <path>` - Change directory
- `exit` or `quit` - Exit the shell
- `Ctrl+C` - Interrupt current command

**Example Sessions:**

*Local Mode:*
```
$ ./cli_client/shell_client.py
Shell CLI Client
Mode: Local API Server
Connected to: http://127.0.0.1:8000
Working directory: /workspace

/workspace $ ls
file1.txt  file2.py  folder/

/workspace $ cd folder

/workspace/folder $ pwd
/workspace/folder

/workspace/folder $ exit
Goodbye!
```

*AgentCore Mode:*
```
$ export TOKEN="your-token"
$ export AGENT_ARN="your-agent-arn"
$ ./cli_client/shell_client.py --agentcore --region us-west-2
Shell CLI Client
Mode: AWS Bedrock AgentCore
Region: us-west-2
Session ID: shell-session-a1b2c3d4e5f6

AgentCore $ Hello, what is 1+1?
[Streaming response from AgentCore...]
The answer is 2.

AgentCore $ exit
Goodbye!
```

## Requirements

- Python 3.8+
- httpx (for shell_client.py)
- aiohttp (for client.py)

Install dependencies:
```bash
pip install httpx aiohttp
```

## API Modes

Both clients support invocations API mode, where all requests are routed through a single `/invocations` endpoint. The shell client exclusively uses invocations mode for all operations.

## Server Logs

When using invocations mode, the server logs each forwarded request:
```
🔀 Invocation → POST /shell/execute
🔀 Invocation → GET /shell/cwd
```
