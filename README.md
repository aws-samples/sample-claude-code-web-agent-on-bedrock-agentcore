# Claude Code Web Agent on Bedrock AgentCore

English | [简体中文](README.zh-CN.md)

A production-ready web agent powered by Claude Code SDK, deployed on AWS Bedrock AgentCore Runtime with React frontend on AWS Amplify.

## Architecture Overview

This solution provides a serverless, scalable Claude Code agent with enterprise-grade features:

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS Amplify (Frontend)                   │
│          React Web UI with Cognito Authentication           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓ HTTPS
┌─────────────────────────────────────────────────────────────┐
│             AWS Bedrock AgentCore Runtime                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  FastAPI Backend (Claude Code SDK Wrapper)          │    │
│  │  • Session Management                               │    │
│  │  • Permission Callbacks                             │    │
│  │  • GitHub OAuth Integration                         │    │
│  │  • Workspace Management (S3)                        │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ↓                    ↓                    ↓
    ┌─────────┐         ┌──────────┐        ┌───────────┐
    │ Bedrock │         │  GitHub  │        │    S3     │
    │ Models  │         │   OAuth  │        │ Workspace │
    └─────────┘         └──────────┘        └───────────┘
```

### Key Components

- **AWS Bedrock AgentCore Runtime**: Serverless container runtime for Claude Code SDK
- **AWS Cognito**: User authentication and authorization
- **GitHub OAuth**: Repository access via AgentCore Identity
- **Amazon S3**: User workspace storage and synchronization
- **AWS Amplify**: Managed React frontend hosting with HTTPS
- **Bedrock Models**: Claude 3.5 Sonnet, Claude 3 Haiku, and other foundation models

## Deployment

### Prerequisites

- AWS CLI configured with appropriate credentials
- Docker installed (for building container images)
- Node.js 18+ and npm
- jq (JSON processor)
- GitHub OAuth App (for repository access)

### Step 1: Configure Deployment

Copy and edit the configuration file:

```bash
cd deploy
cp config.env.template config.env
```

Edit `config.env` and set:
- `AWS_REGION`: Your AWS region
- `GITHUB_OAUTH_CLIENT_ID`: From GitHub OAuth App
- `GITHUB_OAUTH_CLIENT_SECRET`: From GitHub OAuth App
- `COGNITO_*`: (Optional) Existing Cognito pool, or leave empty for auto-creation
- Model configurations (optional, defaults provided)

### Step 2: Build and Push Docker Image

Build the backend container and push to Amazon ECR:

```bash
./deploy/01_build_and_push.sh
```

This script:
- Creates ECR repository
- Builds ARM64 Docker image (required by AgentCore)
- Pushes to ECR

### Step 3: Deploy AgentCore Runtime

Deploy the backend to Bedrock AgentCore:

```bash
./deploy/02_deploy_agentcore.sh
```

This script:
- Creates/updates AgentCore Runtime
- Creates S3 workspace bucket
- Sets up Cognito User Pool (if needed)
- Creates IAM execution role with required permissions
- Configures GitHub OAuth provider
- Exports configuration to `.agentcore_output`

### Step 4: Deploy Amplify Frontend

Deploy the React frontend to AWS Amplify:

```bash
./deploy/03_deploy_amplify.sh
```

This script:
- Creates/updates Amplify app
- Builds and deploys React frontend
- Configures environment variables
- Updates OAuth callback URLs automatically
- Provides Amplify app URL

### Step 5: Update GitHub OAuth App

After deployment, update your GitHub OAuth App settings:

1. Go to https://github.com/settings/developers
2. Select your OAuth App
3. Update **Authorization callback URL** to:
   ```
   https://main.YOUR_AMPLIFY_DOMAIN/oauth/callback
   ```

### Complete Deployment

To run all steps at once:

```bash
./deploy/deploy_all.sh
```

## Key Features

### Enterprise Authentication
- **AWS Cognito**: Secure user registration and login
- **JWT tokens**: Stateless authentication with bearer tokens
- **Email verification**: Optional email domain restrictions

### GitHub Integration
- **OAuth2 Authentication**: Secure GitHub account linking
- **Repository Access**: Clone and manage GitHub repositories
- **AgentCore Identity**: Credential management without storing secrets

### Workspace Management
- **S3 Synchronization**: Persistent workspace storage
- **Multi-user Support**: Isolated workspaces per user
- **High-performance Sync**: Using s5cmd for fast transfers

### Agent Capabilities
- **Multi-session Support**: Handle multiple concurrent sessions
- **Permission System**: User control over agent actions
- **Session Restoration**: Resume previous conversations
- **Real-time Streaming**: SSE for live agent responses

### Model Support
- Claude 3.5 Sonnet (primary)
- Claude 3 Haiku (background tasks)
- Qwen 3 Coder 480B (code-focused)
- LiteLLM proxy support for other providers

## Local Development

For local development and testing without AWS deployment:

### Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- Node.js 18+

### Setup

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Start the backend server
uv run backend/server.py

# In another terminal, start the web client
cd web_client
npm install
npm run dev
```

Visit http://localhost:8080 for the web interface.

### Development Tools

```bash
# Start server with hot reload
uv run uvicorn backend.server:app --host 127.0.0.1 --port 8000 --reload

# Format code
uv run ruff format backend/

# Run tests
uv run pytest
```

## Configuration

### Environment Variables

Key environment variables for the backend (set via `.agentcore_output` after deployment):

- `AGENT_RUNTIME_ARN`: AgentCore Runtime ARN
- `AGENT_RUNTIME_URL`: AgentCore Runtime endpoint URL
- `COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `COGNITO_CLIENT_ID`: Cognito App Client ID
- `GITHUB_OAUTH_PROVIDER_NAME`: GitHub OAuth provider name
- `S3_WORKSPACE_BUCKET`: S3 bucket for workspaces
- `OAUTH_CALLBACK_URL`: OAuth callback URL (Amplify app URL)

### Web Client Environment Variables

Configure in `web_client/.env`:

- `VITE_DEFAULT_SERVER_URL`: AgentCore Runtime URL
- `VITE_COGNITO_REGION`: AWS region
- `VITE_COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `VITE_COGNITO_CLIENT_ID`: Cognito App Client ID
- `VITE_USE_INVOCATIONS`: Use unified invocations endpoint (true/false)

## API Endpoints

The backend exposes the following key endpoints:

- `POST /invocations` - Unified invocation endpoint (primary)
- `POST /sessions` - Create new session
- `POST /sessions/{id}/messages` - Send message
- `GET /sessions/{id}/status` - Get session status
- `GET /sessions/{id}/history` - Get conversation history
- `POST /agentcore/session/stop` - Stop AgentCore session (deprecated, use direct call)
- `GET /github/oauth/token` - Get GitHub OAuth token
- `GET /github/repositories` - List user's repositories
- `POST /workspace/init` - Initialize workspace from S3
- `POST /workspace/clone-git` - Clone Git repository
- `GET /health` - Health check

Full API documentation: `https://YOUR_RUNTIME_URL/docs`

## Architecture Documentation

For detailed documentation, see the `claude/` directory:

- **[Architecture](claude/architecture.md)** - System design and components
- **[Workspace Sync](claude/workspace-sync.md)** - S3 workspace management
- **[Web Client](claude/web-client/readme.md)** - Web interface documentation
- **[User Registration](claude/cognito-signup-guide.md)** - AWS Cognito user signup configuration
- **[Deployment Guide](deploy/README.md)** - Detailed deployment instructions

## Cleanup

To remove all deployed resources:

```bash
./deploy/cleanup.sh
```

This will delete:
- Amplify app
- AgentCore Runtime
- IAM roles
- S3 workspace bucket (optional)
- ECR repository (optional)

## License

Same as the parent Claude Agent SDK project.
