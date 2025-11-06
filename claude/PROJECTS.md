# Project Management

This document describes the project management system that allows users to organize their work into separate workspaces with automatic S3 synchronization.

## Overview

Projects provide isolated workspaces for different tasks or repositories. Each project:
- Has its own directory under `/workspace/{user_id}/{project_name}`
- Syncs to/from S3 independently
- Has its own AgentCore session namespace
- Maintains separate file hierarchies

## AgentCore Session ID Format

The session ID format encodes the user and project information:

### Default Workspace
```
{userId}@workspace
```
Used when no specific project is selected. Files are stored in `/workspace/{user_id}/`.

### Project Workspace
```
{userId}@workspace/{projectName}
```
Used when working in a specific project. Files are stored in `/workspace/{user_id}/{project_name}/`.

## Directory Structure

### Local Filesystem
```
/workspace/
└── {user_id}/
    ├── {project_1}/
    │   ├── .gitkeep
    │   └── [project files...]
    ├── {project_2}/
    │   └── [project files...]
    └── [default workspace files...]
```

### S3 Storage
```
s3://bucket/user_data/
├── {user_id}/
│   ├── .claude/                    # User session data
│   │   └── projects/
│   │       └── {project-key}/
│   │           └── {session-id}.jsonl
│   └── projects/                   # User projects
│       ├── {project_1}/
│       │   ├── .gitkeep
│       │   └── [project files...]
│       └── {project_2}/
│           └── [project files...]
```

## Automatic Synchronization

### Initial Sync (First Request)
When a user makes their first request with a project in the session ID:

1. Server parses `user_id@workspace/project_name` from `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` header
2. Checks if project exists in S3: `s3://bucket/user_data/{user_id}/projects/{project_name}/`
3. If S3 has data:
   - Downloads project files to `/workspace/{user_id}/{project_name}/`
   - Logs sync result with files count
4. If S3 is empty:
   - Skips download
   - Project will be created when user saves files

This is handled automatically in `backend/api/invocations.py` (lines 167-180).

### Periodic Backup
Projects are not currently backed up periodically (only .claude directory is). To add periodic project backup:

```python
# In claude_sync_manager.py, add to _backup_loop():
for user_id in users_to_backup:
    # Backup each project
    projects = await list_projects_from_s3(user_id, bucket, prefix)
    for project in projects:
        await backup_project_to_s3(user_id, project, bucket, prefix)
```

## API Endpoints

### List Projects
```bash
GET /workspace/projects/{user_id}
```

Response:
```json
{
  "user_id": "user123",
  "projects": ["project-1", "project-2"],
  "message": "Found 2 projects"
}
```

Via invocations:
```bash
POST /invocations
{
  "path": "/workspace/projects/{user_id}",
  "method": "GET",
  "path_params": {"user_id": "user123"}
}
```

### Create Project
```bash
POST /workspace/projects
{
  "user_id": "user123",
  "project_name": "my-project"
}
```

Response:
```json
{
  "status": "success",
  "user_id": "user123",
  "project_name": "my-project",
  "local_path": "/workspace/user123/my-project",
  "message": "Project my-project created successfully"
}
```

Creates:
- Local directory: `/workspace/user123/my-project/`
- `.gitkeep` file to ensure directory is not empty
- Syncs to S3: `s3://bucket/user_data/user123/projects/my-project/`

## Web Client Usage

### Project Selector UI

The web client provides a project selector in the sidebar:

1. **Default Workspace**: Shows "Default Workspace" - no project selected
2. **Project List**: Shows all available projects from S3
3. **Create Project**: Click + button to create new project
4. **Active Project**: Highlighted in blue

### Project Workflow

1. **Login**: Projects are loaded from S3 automatically
2. **Select Project**: Click project name to switch
   - Closes current session
   - Updates AgentCore session ID to include project name
   - Files are now in project directory
3. **Create Project**: Click +, enter name, click Create
   - Project created locally and synced to S3
   - Automatically switches to new project
4. **Work in Project**: All file operations now scoped to project directory

### Code Integration

```javascript
// Generate session ID with project
const sessionId = generateAgentCoreSessionId(userId, projectName)
// Example: "user123@workspace/my-project"

// Load projects
const apiClient = createAPIClient(serverUrl)
const result = await apiClient.listProjects(userId)
const projects = result.projects

// Create project
await apiClient.createProject(userId, projectName)

// Switch project
setCurrentProject(projectName)
// Hook automatically updates session ID and reconnects
```

## Environment Variables

Same as workspace sync:
```bash
S3_WORKSPACE_BUCKET=my-workspace-bucket
S3_WORKSPACE_PREFIX=user_data
```

## Implementation Details

### Backend Components

**Session ID Parsing** (`backend/api/invocations.py:56-104`):
```python
def parse_session_and_user_from_headers(request: Request) -> tuple:
    # Parse: user_id@workspace/project_name
    # Returns: (agentcore_session_id, user_id, project_name)
```

**Project Sync Functions** (`backend/core/workspace_sync.py`):
- `list_projects_from_s3()`: Uses s5cmd ls to list project directories
- `sync_project_from_s3()`: Downloads project from S3 (called on first request)
- `backup_project_to_s3()`: Uploads project to S3

**API Routes** (`backend/api/workspace.py:217-342`):
- `GET /workspace/projects/{user_id}`: List projects
- `POST /workspace/projects`: Create project

### Frontend Components

**Session Utils** (`web_client/src/utils/sessionUtils.js`):
```javascript
generateAgentCoreSessionId(userId, projectName = null)
// Returns: "userId@workspace" or "userId@workspace/projectName"
```

**useClaudeAgent Hook** (`web_client/src/hooks/useClaudeAgent.js`):
- Accepts `projectName` parameter
- Regenerates API client when project changes
- Resets session state on project switch

**ProjectSelector Component** (`web_client/src/components/ProjectSelector.jsx`):
- Lists available projects
- Create new project form
- Highlights active project
- Handles project switching

## User Experience

### Scenario 1: New User
1. User logs in
2. No projects found in S3
3. Shows "Default Workspace" only
4. User can create first project or work in default workspace

### Scenario 2: Existing User
1. User logs in
2. Projects loaded from S3: ["website", "api", "mobile"]
3. Default is "Default Workspace"
4. User selects "website" project
5. Session ID becomes `user123@workspace/website`
6. Project files sync from S3 on first request
7. All file operations now in `/workspace/user123/website/`

### Scenario 3: Create New Project
1. User clicks + button
2. Enters "backend-service"
3. Local directory created: `/workspace/user123/backend-service/`
4. `.gitkeep` file added
5. Synced to S3: `s3://bucket/user_data/user123/projects/backend-service/`
6. Project appears in project list
7. Automatically switched to new project

## Monitoring

### Logs

**Project List**:
```
INFO: Listing projects for user: user123
INFO: Found 3 projects for user user123: ['project-1', 'project-2', 'project-3']
```

**Project Creation**:
```
INFO: Creating project my-project for user: user123
INFO: Created local project directory: /workspace/user123/my-project
INFO: ⬆️  Backing up project from /workspace/user123/my-project to s3://bucket/user_data/user123/projects/my-project/
INFO: ✅ Project backup completed: 1 files to S3
```

**Initial Project Sync**:
```
INFO: 🔀 Invocation → GET /sessions/abc123/status
INFO:    🆔 AgentCore Session ID: user123@workspace/my-project
INFO:    👤 User ID: user123
INFO: 📁 Attempting project sync for user user123, project: my-project
INFO: 🔍 Checking if project exists in S3: s3://bucket/user_data/user123/projects/my-project
INFO: ⬇️  Syncing project from s3://... to /workspace/user123/my-project
INFO: ✅ Project sync completed: 15 files from S3
INFO: 📊 Project sync result: success - Successfully synced 15 files from S3
```

### Client Logs

```javascript
console.log('📁 Loaded 3 projects')
console.log('📁 Switching to project: my-project')
console.log('🆔 Generated Agent Core Session ID: user123@workspace/my-project')
console.log('✅ Created project: new-project')
```

## Best Practices

### 1. Project Naming
- Use lowercase with hyphens: `my-project`
- Avoid spaces, underscores, special characters
- Keep names descriptive but concise
- Good: `website`, `api-server`, `mobile-app`
- Avoid: `My Project`, `project_1`, `proj`

### 2. Project Organization
- One repository per project (if cloning from Git)
- Group related work in same project
- Use default workspace for temporary work
- Create projects for long-term work

### 3. Switching Projects
- Save work before switching (files auto-saved to S3 on .claude backup)
- Close active session when switching
- First request to new project triggers sync

### 4. S3 Costs
- Each project syncs independently
- Monitor S3 storage usage
- Use S3 lifecycle policies for old projects
- Consider archiving inactive projects

## Troubleshooting

### Issue: Project not appearing in list

**Check**:
1. S3 bucket configured: `echo $S3_WORKSPACE_BUCKET`
2. s5cmd installed: `which s5cmd`
3. Project exists in S3: `s5cmd ls s3://bucket/user_data/user123/projects/`

**Logs**:
```
ERROR: Error listing projects for user user123: ...
```

### Issue: Project sync not happening

**Check**:
1. AgentCore session ID includes project: `user123@workspace/project-name`
2. Check browser console for session ID
3. Check server logs for sync attempt

**Logs**:
```
⚠️  Warning: Exception during project sync: ...
```

### Issue: Project files not found

**Check**:
1. Project synced successfully (check logs)
2. Files exist locally: `ls /workspace/user123/project-name/`
3. Working directory matches project path

### Issue: Cannot create project

**Possible causes**:
- Project name already exists
- S3 permissions issue
- s5cmd not installed

**Fix**:
```bash
# Check if project exists
ls /workspace/user123/project-name

# Check S3 access
s5cmd ls s3://bucket/user_data/user123/projects/

# Verify s5cmd
s5cmd version
```

## Future Enhancements

Potential improvements:

1. **Periodic Project Backup**: Automatically backup projects every N minutes (like .claude)
2. **Project Templates**: Create projects from templates (React app, Python API, etc.)
3. **Project Deletion**: API to delete projects from S3 and local
4. **Project Sharing**: Share projects between users
5. **Project Archive**: Move inactive projects to S3 Glacier
6. **Project Search**: Search files across all projects
7. **Project Metadata**: Store description, created date, last accessed
8. **Git Integration**: Automatically detect and show Git status per project

## Comparison: Default Workspace vs Projects

| Feature | Default Workspace | Projects |
|---------|-------------------|----------|
| Session ID | `userId@workspace` | `userId@workspace/projectName` |
| Local Path | `/workspace/{userId}/` | `/workspace/{userId}/{projectName}/` |
| S3 Path | N/A (no dedicated S3 path) | `s3://.../projects/{projectName}/` |
| Auto-Sync | No | Yes |
| Use Case | Temporary work, experiments | Long-term work, repositories |
| Isolation | Shared with all non-project work | Isolated per project |

## Related Documentation

- [Workspace Synchronization](./WORKSPACE_SYNC.md) - General S3 sync
- [Claude Directory Sync](./CLAUDE_SYNC.md) - .claude directory backup
- [API Design](../CLAUDE.md) - Overall architecture
