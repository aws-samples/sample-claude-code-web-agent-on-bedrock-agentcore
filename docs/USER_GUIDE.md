# Claude Code Web Agent - User Guide

English | [简体中文](USER_GUIDE.zh-CN.md)

This guide provides step-by-step instructions for deploying and using the Claude Code Web Agent.

## Video Demo

Watch a quick demonstration of the Claude Code Web Agent in action:

<video width="100%" controls>
  <source src="https://du7u4d2q1sjz6.cloudfront.net/cc_on_ac.mp4" type="video/mp4">
  Your browser does not support the video tag. [Download the video](https://du7u4d2q1sjz6.cloudfront.net/cc_on_ac.mp4)
</video>

---

## Table of Contents

1. [Deployment Guide](#deployment-guide)
2. [User Registration and Login](#user-registration-and-login)
3. [Project Management](#project-management)
4. [Creating Sessions and Chatting with Agent](#creating-sessions-and-chatting-with-agent)
5. [File Management and Preview](#file-management-and-preview)
6. [Git Operations](#git-operations)
7. [Terminal Usage](#terminal-usage)
8. [Disconnect and Reconnect](#disconnect-and-reconnect)

---

## Deployment Guide

### Prerequisites

Before deploying the Claude Code Web Agent, ensure you have:

- **AWS CLI** configured with appropriate credentials
- **Docker** installed (for building container images)
- **Node.js 18+** and npm
- **jq** (JSON processor)
- **GitHub OAuth App** (for repository access)

### Step 1: Configure Deployment Settings

1. Navigate to the deployment directory:
   ```bash
   cd deploy
   ```

2. Copy the configuration template:
   ```bash
   cp config.env.template config.env
   ```

3. Edit `config.env` and configure the following:
   - **AWS_REGION**: Your AWS region (e.g., `us-west-2`)
   - **GITHUB_OAUTH_CLIENT_ID**: From your GitHub OAuth App
   - **GITHUB_OAUTH_CLIENT_SECRET**: From your GitHub OAuth App
   - **COGNITO_*** (Optional): Leave empty to auto-create new Cognito User Pool
   - **AVAILABLE_MODELS**: Comma-separated list of models for the web client
   - **Model configurations**: Optional, defaults are provided

### Step 2: Build and Push Docker Image

Build the backend container and push to Amazon ECR:

```bash
./deploy/01_build_and_push.sh
```

This script will:
- Create an ECR repository
- Build an ARM64 Docker image (required by AgentCore)
- Push the image to ECR

### Step 3: Deploy AgentCore Runtime

Deploy the backend to Bedrock AgentCore:

```bash
./deploy/02_deploy_agentcore.sh
```

This script will:
- Create or update AgentCore Runtime
- Create an S3 workspace bucket
- Set up Cognito User Pool (if not provided)
- Create IAM execution role with required permissions
- Configure GitHub OAuth provider
- Export configuration to `.agentcore_output`

### Step 4: Deploy Amplify Frontend

Deploy the React frontend to AWS Amplify:

```bash
./deploy/03_deploy_amplify.sh
```

This script will:
- Create or update Amplify app
- Build and deploy React frontend
- Configure environment variables
- Update OAuth callback URLs automatically
- Provide the Amplify app URL

### Step 5: Update GitHub OAuth App

After deployment, update your GitHub OAuth App settings:

1. Go to https://github.com/settings/developers
2. Select your OAuth App
3. Update **Authorization callback URL** to:
   ```
   https://main.YOUR_AMPLIFY_DOMAIN/oauth/callback
   ```

### Quick Deployment

To run all deployment steps at once:

```bash
./deploy/deploy_all.sh
```

---

## User Registration and Login

### Understanding the Authentication System

The Claude Code Web Agent uses **AWS Cognito** for user authentication, providing secure registration, login, and session management.

### Registering a New Account

1. **Access the Application**: Navigate to your deployed Amplify URL (e.g., `https://main.YOUR_AMPLIFY_DOMAIN`)

2. **Click "Sign Up"**: On the login page, click the "Sign Up" button at the bottom

3. **Fill Registration Form**:
   - **Username**: Choose a unique username (letters, numbers, and underscores)
   - **Email**: Enter a valid email address (will be used for verification)
   - **Password**: Create a strong password (minimum 8 characters, including uppercase, lowercase, numbers, and special characters)

4. **Submit Registration**: Click the "Sign Up" button

5. **Email Verification**:
   - Check your email inbox for a verification code
   - Enter the 6-digit verification code on the confirmation page
   - Click "Confirm" to activate your account

6. **Auto-Login**: After successful confirmation, you'll be automatically logged in

### Logging In

1. **Access the Login Page**: Navigate to the application URL

2. **Enter Credentials**:
   - **Username or Email**: Enter your username or email address
   - **Password**: Enter your password

3. **Click "Sign In"**: Click the sign-in button to authenticate

4. **Connection Modal**: After login, you'll see a "Connect to Server" modal
   - Click **"Connect to Server"** to start background services and enable all features

![Connect to Server](assets/connect_page.webp)

### Troubleshooting Login Issues

- **Incorrect Password**: Double-check your password and try again
- **Email Not Verified**: Check your email and complete verification
- **Account Locked**: Contact your administrator if you've exceeded login attempts
- **Forgot Password**: Use the password reset feature (if enabled)

---

## Project Management

### Understanding Projects and Workspaces

**Projects** in Claude Code Web Agent are isolated workspaces where you can work on different codebases. Each project has its own:
- Working directory in `/workspace/{project_name}`
- Git repository (optional)
- Session history
- File structure

![Project Management](assets/project_page.webp)

### Creating a New Project

1. **Navigate to Projects Tab**: Click the folder icon (📁) in the left sidebar

2. **Click "Create Project"**: Click the "+ Create Project" button at the top

3. **Enter Project Details**:
   - **Project Name**: Choose a descriptive name (alphanumeric, hyphens, underscores)
   - The project will be created in `/workspace/{project_name}`

4. **Click "Create"**: Confirm project creation

5. **Auto-Switch**: The system will automatically switch to your new project

![Create Project](assets/project_create.webp)

### Importing from GitHub

1. **Navigate to Projects Tab**: Click the folder icon in the left sidebar

2. **Click "Import from GitHub"**: Find the GitHub import button

3. **Authenticate with GitHub** (first time only):
   - Click the GitHub icon in the header (top-right)
   - Authorize the application to access your GitHub account
   - Wait for confirmation (green checkmark)

4. **Enter Repository URL**:
   - **HTTPS URL**: `https://github.com/username/repository.git`
   - **SSH URL**: `git@github.com:username/repository.git` (requires SSH key setup)
   - **Optional**: Specify branch name (defaults to main branch)
   - **Optional**: Enable shallow clone for faster cloning

5. **Click "Clone"**: Start the cloning process

6. **Monitor Progress**: Watch the cloning progress in the console

7. **Auto-Switch**: After successful clone, the project will be activated

![Import from GitHub](assets/project_github_import.webp)

### Switching Between Projects

1. **Open Project Switcher**:
   - Click the project name in the header (shows current project or "Default Workspace")
   - Or click the folder icon in the sidebar and select a project from the list

2. **Select Project**: Click on any project in the list

3. **Confirm Switch** (if you have an active session):
   - Warning: Switching will close your current session
   - Click "OK" to proceed

4. **Automatic Backup**: Your current project is automatically backed up to S3 before switching

5. **Project Activation**: The new project's workspace is loaded and ready to use

### Project Features

- **Automatic S3 Backup**: Projects are automatically synced to S3 when switching
- **Isolated Sessions**: Each project has its own session history
- **Working Directory**: Projects have dedicated working directories
- **Git Integration**: Full git support per project
- **File Browser**: Browse and manage files within each project

---

## Creating Sessions and Chatting with Agent

### Understanding Sessions

A **session** represents a conversation with the Claude agent. Each session maintains:
- Conversation history
- Agent context and memory
- Tool usage history
- Working directory context

### Creating a New Session

1. **Navigate to Sessions Tab**: Click the chat icon (💬) in the left sidebar

2. **Click "New Session"** (or the + button):
   - If you have no active session, the button will say "Start Session"
   - If you have an active session, it will say "Clear Session"

3. **Session Initialization**:
   - A unique session ID is generated
   - The agent is initialized with your working directory context
   - You'll see "✅ Connected to Claude Agent" in the chat

4. **Session Info**: The session ID is displayed in the chat header

### Chatting with the Agent

1. **Type Your Message**: Enter your request in the input box at the bottom:
   ```
   Create a Python script that reads a CSV file and generates a summary report
   ```

2. **Send Message**: Click the send button (➤) or press Enter

3. **Agent Response**: The agent will:
   - Stream its response in real-time
   - Use tools as needed (file operations, terminal commands, etc.)
   - Show tool usage in the chat (e.g., "Using tool: Edit")

4. **Review Output**: Check the agent's text responses and tool outputs

![Session and Chat](assets/session_agent_chat.webp)

### Permission System

The agent requires permission for certain operations:

1. **Permission Request Appears**: When the agent needs to perform a write operation, you'll see a yellow permission box

2. **Review the Request**:
   - **Tool Name**: The tool being used (e.g., "Edit", "Write")
   - **Parameters**: Details of the operation (file path, content, etc.)
   - **Suggested Changes**: What the agent wants to modify

3. **Grant or Deny Permission**:
   - **✓ Allow**: Grant permission for this operation
   - **⚡ Apply Suggestions**: Apply suggested changes and grant permission
   - **✗ Deny**: Reject the operation

4. **Continue Conversation**: After your decision, the agent continues

### Model Selection

You can switch models during a session:

1. **Current Model**: Displayed in the chat header (e.g., "sonnet-4-5-...")

2. **Click Model Name**: Opens the model selector dropdown

3. **Select Model**: Choose from available models:
   - **Claude Sonnet 4.5**: Best for complex reasoning and coding
   - **Claude Haiku 4.5**: Faster, good for simple tasks
   - **Qwen Coder**: Specialized for coding tasks

4. **Model Switch**: The agent will use the new model for subsequent messages

### Managing Sessions

**Resume Previous Session**:
1. Navigate to Sessions Tab
2. Click on any session in the session list
3. The conversation history will be loaded

**Clear Current Session**:
1. Click "Clear Session" in the Sessions tab
2. Confirm the action
3. A new session is created, losing current context

**Session Persistence**:
- Sessions are automatically saved to disk
- Sessions can be resumed even after disconnecting
- Each session file is stored in `~/.claude/projects/`

---

## File Management and Preview

### Understanding the File Browser

The **File Browser** shows your current project's file structure and allows you to navigate, preview, and manage files.

![File Browser](assets/file_explorer.webp)

### Navigating Files

1. **Access File Browser**: Click the file icon (📄) in the left sidebar

2. **Browse Directories**:
   - Click on folder names to expand/collapse them
   - The current path is shown at the top
   - Use the breadcrumb navigation to go up directories

3. **File Icons**:
   - 📁 Folder
   - 📄 File
   - 🔧 Configuration file (.json, .yaml, .toml, etc.)
   - 🐍 Python file (.py)
   - 📜 JavaScript file (.js, .jsx, .ts, .tsx)

### Previewing Files

1. **Click on a File**: Click any file name in the file browser

2. **Preview Panel Opens**: A preview panel appears on the right side

3. **File Content Display**:
   - **Text Files**: Shows syntax-highlighted content
   - **Images**: Displays the image
   - **Large Files**: Shows first portion with "Load More" option

4. **Syntax Highlighting**: Automatic language detection for code files

5. **Close Preview**: Click the ✗ button in the preview header

### File Operations via Agent

You can ask the agent to perform file operations:

```
Create a new file called main.py with a Hello World program
```

```
Read the contents of config.json and explain what each setting does
```

```
Modify utils.py to add error handling to the process_data function
```

### File Refresh

- **Automatic Refresh**: Files are automatically refreshed when you send messages to the agent
- **Manual Refresh**: The file browser updates after agent operations
- **Real-time Updates**: Changes made by the agent appear immediately

---

## Git Operations

### Understanding Git Integration

The **Git Panel** provides version control capabilities, allowing you to view changes, create commits, and push to remote repositories.

![Git Panel](assets/git_panel.webp)

### Viewing Git Status

1. **Access Git Tab**: Click the git branch icon in the left sidebar

2. **Git Status Display**:
   - **Current Branch**: Shown as a badge in the header
   - **Staged Files**: Files ready to be committed (green +)
   - **Unstaged Files**: Modified files not yet staged (blue M)
   - **Untracked Files**: New files not in git (📄)

3. **File Change Icons**:
   - **M** (Modified): File has been changed
   - **A** (Added): New file staged
   - **D** (Deleted): File has been removed

4. **Automatic Refresh**: Git status refreshes when you switch to the Git tab

### Viewing Commit History

1. **Recent Commits Section**: Scroll down to see recent commits

2. **Commit Information**:
   - **Commit Hash**: Short hash (first 7 characters)
   - **Author**: Who made the commit
   - **Date**: When the commit was made
   - **Message**: Commit message

3. **Expand Commit**: Click on any commit to see changed files

4. **File Changes**: Shows which files were modified in that commit

### Creating a Commit

1. **Review Changes**: Check the files in the "Changes" section

2. **Click "Commit" Button**: Opens the commit form

3. **Write Commit Message**:
   - First line: Brief summary (50 characters max recommended)
   - Blank line (optional)
   - Detailed description (if needed)

4. **Select Files** (optional):
   - By default, all changed files are included
   - Uncheck files you don't want to commit
   - Or leave all checked to commit everything

5. **Click "Create Commit"**: Finalizes the commit

6. **Confirmation**: You'll see "✓ Commit created successfully"

### Pushing to Remote

1. **Ensure Commits Exist**: Check that you have local commits to push

2. **Click "Push" Button**: Located in the Recent Commits section

3. **Confirm Push**: A confirmation dialog appears

4. **GitHub Authentication** (if needed):
   - If not authenticated, you'll be prompted to authenticate with GitHub
   - Follow the GitHub OAuth flow

5. **Push Progress**: Wait for the push to complete

6. **Success Message**: "Successfully pushed commits"

### Git Operations via Agent

You can also ask the agent to perform git operations:

```
Show me the git status
```

```
Create a commit with message "Add user authentication feature"
```

```
Push my changes to the remote repository
```

### Manual Refresh

- **Refresh Button**: Click the refresh icon (🔄) in the Git panel header
- **Refreshes**: Both git status and commit history
- **Use Case**: Update after external git operations

---

## Terminal Usage

### Understanding the Integrated Terminal

The **Terminal** provides a full-featured command-line interface running on the server, allowing you to execute commands, run scripts, and interact with your workspace.

![Terminal](assets/terminal.webp)

### Opening the Terminal

1. **Click Terminal Icon**: Click the terminal icon (⌨️) in the header (top-right)

2. **Terminal Panel Opens**: A terminal panel slides in from the right side

3. **Initial State**: The terminal is initialized in your current project directory

### Using the Terminal

1. **Run Commands**: Type any shell command and press Enter:
   ```bash
   ls -la
   ```
   ```bash
   python script.py
   ```
   ```bash
   npm install
   ```

2. **Output Display**: Command output appears in real-time

3. **Color Support**: ANSI colors are supported for better readability

4. **Command History**:
   - Press ↑ to cycle through previous commands
   - Press ↓ to go forward in history

5. **Tab Completion**: Tab key for auto-completion (if supported by shell)

### Terminal Features

- **Working Directory**: Always starts in your current project directory
- **Environment**: Full shell environment with all system tools
- **Long-running Commands**: Supports commands that run indefinitely
- **Interactive Programs**: Can run interactive programs like vim, nano, etc.
- **Multiple Lines**: Supports multi-line input (use Shift+Enter)

### Common Use Cases

**Package Management**:
```bash
npm install express
pip install requests
uv add anthropic
```

**Running Scripts**:
```bash
python main.py
node server.js
./run_tests.sh
```

**Git Operations**:
```bash
git status
git pull origin main
git log --oneline -10
```

**File Operations**:
```bash
cat config.json
grep -r "TODO" src/
find . -name "*.py"
```

**Build and Test**:
```bash
npm run build
pytest tests/
cargo build --release
```

### Resizing the Terminal

1. **Resize Handle**: Position your mouse on the left edge of the terminal panel

2. **Drag to Resize**: Click and drag left or right to adjust width

3. **Size Constraints**: Terminal width is constrained between 400px and 1000px

### Closing the Terminal

1. **Click Terminal Icon Again**: Toggle the terminal off

2. **Or Click ✗**: Click the close button in the terminal header

3. **Session Persists**: The terminal session remains active in the background

---

## Disconnect and Reconnect

### Understanding Connection States

The Claude Code Web Agent has two connection states:
- **Server Connected**: Background services running, can use all features
- **Server Disconnected**: Background services stopped, limited functionality

### Disconnecting from Server

Disconnecting stops all background services but keeps you logged in.

1. **Click Disconnect Button**: Click the ✗ circle icon in the header

2. **Confirm Disconnect**: A confirmation dialog appears:
   ```
   Disconnect from server?

   This will stop all background requests and close any active sessions.
   ```

3. **Click "OK"**: Confirms the disconnect action

4. **Disconnect Process**:
   - Current agent session is closed (if active)
   - Waits 3 seconds for pending requests to complete
   - Stops AgentCore runtime session
   - Background services (health checks, polling) are stopped

5. **Disconnect Modal Appears**: You'll see the connection modal with options:
   - **Connect to Server**: Reconnect and resume work
   - **Force Stop AgentCore**: Emergency stop (if needed)
   - **Log Out**: Log out of the application

### Reconnecting to Server

1. **Click "Connect to Server"**: On the disconnect modal

2. **Background Services Start**:
   - Health check polling resumes
   - Session polling resumes
   - API connection established

3. **Ready to Use**: All features are now available again

4. **Auto-resume**: Your previous project and settings are preserved

### Logging Out

Logging out stops all services and ends your session.

1. **Click Logout Button**: Click the logout icon in the header

2. **Confirm Logout**: A confirmation dialog appears:
   ```
   Logout?

   This will stop all background requests, close any active sessions, and log you out.
   ```

3. **Click "OK"**: Confirms the logout action

4. **Logout Process**:
   - Disconnects active agent session
   - Waits 3 seconds for pending requests
   - Stops AgentCore runtime session
   - Signs out from Cognito

5. **Redirect to Login**: You're redirected to the login page

### Force Stop AgentCore (Emergency)

If the system becomes unresponsive, you can force stop:

1. **Access Disconnect Modal**: Disconnect from server first

2. **Click "Force Stop AgentCore"**: Red button in the modal

3. **Confirm Action**: This immediately stops the runtime session

4. **Use Case**: Only use when normal disconnect fails

### Reconnection Scenarios

**After Disconnect**:
- All settings preserved
- Project selection preserved
- No active session (must create new one)
- Background services restarted

**After Logout**:
- Must log in again
- Settings preserved in browser
- Project selection preserved
- No active session

**After Force Stop**:
- Must reconnect to server
- May need to wait a few seconds for runtime to restart
- All state is preserved

### Best Practices

- **Normal Work**: Keep server connected
- **Long Breaks**: Disconnect to save resources
- **End of Day**: Log out for security
- **Switching Users**: Always log out first
- **Troubleshooting**: Use force stop as last resort

---

## Tips and Best Practices

### Session Management

- **Create descriptive session names**: Use clear naming for easy identification
- **Resume old sessions**: Continue previous work without losing context
- **Clear when starting new tasks**: Start fresh for unrelated work

### File Organization

- **Use projects for different repositories**: Keep codebases separate
- **Regular commits**: Commit frequently with clear messages
- **Backup to S3**: Project switching automatically backs up to S3

### Agent Interaction

- **Be specific**: Provide clear, detailed instructions to the agent
- **Review permissions**: Always review what the agent wants to change
- **Use context**: Reference files and previous conversation context

### Performance

- **Close unused panels**: Hide preview and terminal when not needed
- **Disconnect when idle**: Save resources during breaks
- **Use appropriate models**: Use Haiku for simple tasks, Sonnet for complex ones

### Security

- **Log out on shared computers**: Always log out when done
- **Review file changes**: Check what the agent modified before committing
- **Don't share credentials**: Never share your login credentials

---

## Troubleshooting

### Cannot Connect to Server

- **Check URL**: Verify the Amplify URL is correct
- **Check Deployment**: Ensure AgentCore runtime is deployed
- **Check Logs**: Look at browser console for errors

### Session Creation Fails

- **Server disconnected**: Connect to server first
- **Check permissions**: Ensure IAM roles are configured correctly
- **Check Bedrock access**: Verify model access in Bedrock console

### File Operations Fail

- **Check permissions**: File system permissions may be restricted
- **Check disk space**: S3 bucket may be full
- **Refresh browser**: Try refreshing the page

### Git Operations Fail

- **Authenticate GitHub**: Click GitHub icon and authenticate
- **Check repository**: Verify repository URL is correct
- **Check credentials**: May need to re-authenticate

### Terminal Not Working

- **Reload page**: Try refreshing the browser
- **Check connection**: Ensure server is connected
- **Check firewall**: Corporate firewall may block WebSocket connections

---

## Support and Resources

### Documentation

- **README.md**: Architecture and deployment overview
- **WORKSPACE_SYNC.md**: Workspace management details
- **Backend Documentation**: API reference in `backend/` directory

### Getting Help

- **GitHub Issues**: Report bugs and request features
- **AWS Support**: Contact AWS support for infrastructure issues
- **Community**: Join discussions in project forums

### Additional Resources

- **Amazon Bedrock AgentCore Documentation**: https://docs.aws.amazon.com/bedrock-agentcore/
- **AWS Bedrock Documentation**: https://docs.aws.amazon.com/bedrock/
- **AWS Amplify Documentation**: https://docs.aws.amazon.com/amplify/