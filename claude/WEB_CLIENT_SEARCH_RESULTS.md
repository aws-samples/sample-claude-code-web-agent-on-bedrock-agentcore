# Web Client Search Results - Connect to Server & Logout

## Search Query Completed

Searched for:
- Connect to Server page component
- Force Stop button implementation
- Authentication/session management
- Logout functionality
- React components (JSX/TSX files)

## Absolute File Paths

### Primary Component Files

1. **Main App Component**
   - Path: `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/web_client/src/App.jsx`
   - Contains: Connect to Server modal (lines 668-730), logout handler (lines 373-404), force stop handler (lines 457-475)
   - Size: 945 lines

2. **Header Component**
   - Path: `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/web_client/src/components/Header.jsx`
   - Contains: Logout button with icon (lines 78-82), connection status display
   - Size: 88 lines

3. **Authentication Hook**
   - Path: `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/web_client/src/hooks/useAuth.jsx`
   - Contains: AuthProvider context, login/signup/logout functions, token refresh logic
   - Size: 298 lines

4. **Authentication Utilities**
   - Path: `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/web_client/src/utils/authUtils.js`
   - Contains: Token management, AgentCore session ID generation, global auth error handler
   - Size: 162 lines

5. **API Client**
   - Path: `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/web_client/src/api/client.js`
   - Contains: DirectAPIClient and InvocationsAPIClient classes, stopAgentCoreSession() method
   - Size: 1329 lines

### Supporting Files

6. **Cognito Configuration**
   - Path: `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/web_client/src/config/cognito.js`
   - Contains: Amplify configuration for AWS Cognito

7. **Login Component**
   - Path: `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/web_client/src/components/Login.jsx`
   - Contains: Login form UI

8. **Signup Component**
   - Path: `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/web_client/src/components/Signup.jsx`
   - Contains: Registration form UI

### Documentation Files

9. **This Document**
   - Path: `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/claude/web-client-logout-force-stop.md`
   - Contains: Comprehensive documentation of all logout and force stop functionality

---

## Key Code Snippets

### Connect to Server Modal
Located in: `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/web_client/src/App.jsx` (lines 668-730)

### Force Stop Button Handler
Located in: `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/web_client/src/App.jsx` (lines 457-475)

### Logout Button
Located in: `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/web_client/src/components/Header.jsx` (lines 78-82)

### Logout Handler
Located in: `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/web_client/src/App.jsx` (lines 373-404)

### stopAgentCoreSession API Method
Located in: `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/web_client/src/api/client.js` (lines 568-608 and 854-894)

### AgentCore Session ID Generation
Located in: `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/web_client/src/utils/authUtils.js` (lines 47-92)

---

## Component Architecture

```
App.jsx
├── Modal Overlay (serverDisconnected)
│   ├── Connect to Server Button → handleReconnectServer()
│   └── Force Stop AgentCore Button → handleForceStopAgentCore()
├── Header Component
│   └── Logout Button → handleLogout()
├── Main Content (SessionList, FileBrowser, etc.)
└── useAuth Context
    ├── user state
    ├── login/signup functions
    ├── logout function
    └── token management

useAuth Context (useAuth.jsx)
├── AuthProvider Component
├── User state management
├── Cognito API integration (via AWS Amplify)
└── Token refresh logic

API Client (client.js)
├── DirectAPIClient
│   └── stopAgentCoreSession()
└── InvocationsAPIClient
    └── stopAgentCoreSession()

Auth Utilities (authUtils.js)
├── Token management
├── AgentCore session ID generation
└── Global auth error handler
```

---

## State Flow Diagram

```
App Mount
  ↓
serverDisconnected = true (default)
  ↓
Show Modal: "Connect to Server"
  ├── Button: "Connect to Server" → setServerDisconnected(false)
  └── Button: "Force Stop AgentCore" → apiClient.stopAgentCoreSession()
       ↓
       └── API: POST /stopruntimesession (with session ID header)

User Logout (Header.logout button)
  ↓
handleLogout()
  ├── Confirm: window.confirm()
  ├── Stop AgentCore: apiClient.stopAgentCoreSession()
  ├── Disconnect: disconnect()
  ├── Logout: logout() [from useAuth]
  └── UI: Redirect to Login page
```

---

## LocalStorage Keys

Used by the web client:

1. `claude-agent-settings` - Stores server URL, CWD, model, etc.
2. `claude-agent-server-disconnected` - Stores server connection state

Location where persisted:
- App.jsx lines 21-22: Key definitions
- App.jsx lines 50-60: Settings loading
- App.jsx lines 107-116: Server disconnected state loading
- App.jsx lines 149-156: Settings saving
- App.jsx lines 158-165: Server disconnected state saving

---

## Integration Points

### 1. With Backend API
- Endpoint: `/stopruntimesession` - Force stop AgentCore
- Header: `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id`
- Header: `Authorization: Bearer {token}`

### 2. With AWS Cognito
- Via AWS Amplify SDK
- Signs in users, manages tokens
- Handles session refresh
- Secure httpOnly cookies

### 3. With AgentCore
- Session ID format: `{user_id}@workspace[/{project}]`
- Extracted from JWT token 'sub' claim
- Environment variables:
  - `VITE_WORKSPACE_MODE` - Determines session ID format
  - `VITE_USE_INVOCATIONS` - API routing mode

---

## Next Steps for Implementation

If adding logout to other components:

1. Import useAuth: `import { useAuth } from '../hooks/useAuth.jsx'`
2. Get logout function: `const { logout } = useAuth()`
3. Call on button click: `await logout()`
4. User automatically redirected to login

---

## Related Documentation

See also:
- `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/claude/web-client-logout-force-stop.md`
- `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/CLAUDE.md`
- `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/claude/cognito-error-handling.md`
- `/Users/cfu/git/203_aws_sample/sample-claude-code-web-agent-on-bedrock-agentcore/claude/SESSION_ID_FLOW.md`

