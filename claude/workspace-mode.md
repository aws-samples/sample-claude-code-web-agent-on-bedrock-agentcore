# Workspace Mode Configuration

The web client supports two working modes for managing AgentCore session IDs and project isolation.

## Modes

### 1. Workspace Mode (`VITE_WORKSPACE_MODE=true`)

**AgentCore Session ID Format:** `userid@workspace`

**Characteristics:**
- All operations happen in `/workspace` directory
- Project switching doesn't change the session ID
- Shared context across all projects
- All API requests (files, GitHub auth, shell, etc.) use the same session ID
- Suitable when you want a single unified workspace

**Use Case:**
- Working on related projects that share context
- Need consistent environment across project switches
- Prefer simple session management

### 2. Project Mode (`VITE_WORKSPACE_MODE=false`, **default**)

**AgentCore Session ID Format:** `userid@workspace/project`

**Characteristics:**
- Operations scoped to `/workspace/project` directory
- Each project has its own isolated session ID
- Project switching changes the session ID
- Separate context per project
- All API requests use project-specific session ID
- Suitable for isolated project environments

**Use Case:**
- Working on unrelated projects
- Need strict isolation between projects
- Each project has different requirements/dependencies

## Configuration

### Environment Variable

Add to `web_client/.env`:

```bash
# Workspace Mode Configuration
# Set to 'true' for workspace mode, 'false' for project mode
VITE_WORKSPACE_MODE=false  # Default: project mode
```

### How It Works

1. **Session ID Generation**
   ```javascript
   // In authUtils.js
   export async function getAgentCoreSessionId(project = null) {
     const workspaceMode = import.meta.env.VITE_WORKSPACE_MODE === 'true'

     if (workspaceMode || !project) {
       return `${userId}@workspace`
     } else {
       return `${userId}@workspace/${project}`
     }
   }
   ```

2. **Component Integration**
   - All components (SessionList, FileBrowser, FilePreview, TerminalPTY, etc.) receive `currentProject` prop
   - API clients are initialized with project-aware session IDs
   - Switching projects updates session ID in project mode only

3. **API Requests**
   - All API requests include `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` header
   - Header value determined by current mode and project
   - Ensures operations target correct workspace/project

## Examples

### Workspace Mode Example

```bash
# .env
VITE_WORKSPACE_MODE=true
```

```
User: alice@example.com (userId: abc-123)
Current Project: llm-performance-viz

Session ID: abc-123@workspace

# Switching to another project
Current Project: example

Session ID: abc-123@workspace (unchanged)
```

### Project Mode Example (Default)

```bash
# .env
VITE_WORKSPACE_MODE=false
```

```
User: alice@example.com (userId: abc-123)
Current Project: llm-performance-viz

Session ID: abc-123@workspace/llm-performance-viz

# Switching to another project
Current Project: example

Session ID: abc-123@workspace/example (changed)
```

## Deployment

When deploying to AWS Amplify:

1. Update `web_client/.env` with desired mode
2. Run deployment script:
   ```bash
   cd deploy
   ./deploy.sh
   ```
3. Environment variables are automatically synced to Amplify

## Backend Compatibility

The backend API server should handle both session ID formats:

- `userid@workspace` - Operations in `/workspace`
- `userid@workspace/project` - Operations in `/workspace/project`

Session isolation and file paths are managed by the backend based on the session ID format.
