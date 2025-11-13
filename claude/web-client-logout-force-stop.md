# Web Client: Logout and Force Stop Implementation

## Overview

This document details the Connect to Server page component, Force Stop button implementation, authentication/session management, and logout functionality in the React web client.

## File Structure

### Key Component Files

1. **App.jsx** - Main application component (lines 668-730)
   - Location: `/web_client/src/App.jsx`
   - Renders the "Connect to Server" modal when `serverDisconnected` is true
   - Manages all server connection state and session lifecycle

2. **Header.jsx** - Header component with logout button
   - Location: `/web_client/src/components/Header.jsx`
   - Displays user info, connection status, and action buttons
   - Includes logout button with `LogOut` icon from lucide-react

3. **useAuth.jsx** - Authentication context and hook
   - Location: `/web_client/src/hooks/useAuth.jsx`
   - Implements AWS Amplify authentication with Cognito
   - Provides login, signup, logout, and token management functions

4. **authUtils.js** - Authentication utilities
   - Location: `/web_client/src/utils/authUtils.js`
   - Token management and validation
   - AgentCore session ID generation from JWT claims

5. **client.js** - API client abstraction
   - Location: `/web_client/src/api/client.js`
   - Two modes: Direct API and Invocations mode
   - Implements `stopAgentCoreSession()` method

---

## Component: Connect to Server Page

### Location and Rendering

**File**: `/web_client/src/App.jsx` (lines 668-730)

The "Connect to Server" page is a modal overlay that appears when `serverDisconnected === true`. It's positioned as a full-screen modal with:
- Fixed positioning covering entire viewport
- Semi-transparent dark overlay (rgba 0,0,0,0.8)
- Centered white modal box
- High z-index (10000) to appear above all content

### Modal Structure

```jsx
{serverDisconnected && (
  <div style={{...}}>  {/* Modal overlay */}
    <div style={{...}}>  {/* Modal box */}
      <h2>Connect to Server</h2>
      <p>Click the button below to connect to the server...</p>
      <div style={{...}}>
        <button onClick={handleReconnectServer}>
          Connect to Server
        </button>
        <button onClick={handleForceStopAgentCore}>
          Force Stop AgentCore
        </button>
      </div>
      <p>Server: {settings.serverUrl}</p>
    </div>
  </div>
)}
```

### Modal Triggers

The modal appears when:
1. App initializes with `serverDisconnected = true` (default state)
2. User explicitly disconnects via "Disconnect from Server" button
3. Server connection is lost and state is persisted to localStorage

### Local Storage Persistence

```javascript
const SERVER_DISCONNECTED_KEY = 'claude-agent-server-disconnected'

// Load on mount
const [serverDisconnected, setServerDisconnected] = useState(() => {
  const saved = localStorage.getItem(SERVER_DISCONNECTED_KEY)
  return saved ? JSON.parse(saved) : true  // Default to true
})

// Save when changes
useEffect(() => {
  localStorage.setItem(SERVER_DISCONNECTED_KEY, JSON.stringify(serverDisconnected))
}, [serverDisconnected])
```

---

## Force Stop Button Implementation

### Location

**File**: `/web_client/src/App.jsx` (lines 457-475)

### Handler Function: `handleForceStopAgentCore()`

```javascript
const handleForceStopAgentCore = async () => {
  console.log('🛑 Force stopping AgentCore session...')
  console.log('⚠️  Warning: This will directly stop the AgentCore runtime session without closing active sessions')
  try {
    const agentCoreSessionId = await getAgentCoreSessionId(currentProject)
    const apiClient = createAPIClient(settings.serverUrl, agentCoreSessionId)

    // Directly stop AgentCore runtime session without any invocations requests
    // This bypasses /invocations endpoint and calls stopRuntimeSession directly
    console.log('🛑 Stopping AgentCore runtime session directly...')
    await apiClient.stopAgentCoreSession('DEFAULT')

    console.log('✅ AgentCore session stopped successfully')
    alert('AgentCore session stopped successfully')
  } catch (error) {
    console.error('Failed to stop AgentCore session:', error)
    alert(`Failed to stop AgentCore session: ${error.message}`)
  }
}
```

### API Implementation

**File**: `/web_client/src/api/client.js` (lines 568-608 and 854-894)

The `stopAgentCoreSession()` method exists in both DirectAPIClient and InvocationsAPIClient:

```javascript
async stopAgentCoreSession(qualifier = 'DEFAULT') {
  const authHeaders = await getAuthHeaders(true) // Include session ID and bearer token
  const sessionId = authHeaders['X-Amzn-Bedrock-AgentCore-Runtime-Session-Id']

  if (!sessionId) {
    console.warn('No active AgentCore session found')
    return { status: 'no_session', message: 'No active AgentCore session found' }
  }

  // Construct stopruntimesession endpoint URL directly from baseUrl
  const url = `${this.baseUrl}/stopruntimesession?qualifier=${encodeURIComponent(qualifier)}`

  console.log(`Stopping AgentCore session ${sessionId} at ${url}`)

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': authHeaders['Authorization'],
      'Content-Type': 'application/json',
      'X-Amzn-Bedrock-AgentCore-Runtime-Session-Id': sessionId
    }
  })

  // Handle 404 as success (session already terminated or not found)
  if (response.status === 404) {
    console.log('Session not found or already terminated')
    return { status: 'not_found', message: 'Session not found or already terminated' }
  }

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Failed to stop AgentCore session: ${response.status} ${errorText}`)
  }

  try {
    return await response.json()
  } catch {
    return { status: 'success', message: 'Session stopped' }
  }
}
```

### Key Points

- Calls `/stopruntimesession` endpoint with `qualifier=DEFAULT`
- Sends AgentCore session ID in `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` header
- Treats 404 response as success (session already stopped)
- Does NOT close active agent sessions (just stops the AgentCore runtime)
- Returns status object with success/error information

---

## Authentication/Session Management Implementation

### Authentication Architecture

The authentication system uses **AWS Amplify with Cognito**:

**Provider**: `/web_client/src/hooks/useAuth.jsx`

Key features:
- Amplify configuration for Cognito
- React Context API for state management
- Automatic token refresh (5-minute threshold)

### Auth State

```javascript
const [user, setUser] = useState(null)
const [initializing, setInitializing] = useState(true)
const [loading, setLoading] = useState(false)
const [error, setError] = useState(null)
```

User object structure:
```javascript
{
  username: string,
  userId: string,
  signInDetails: object,
  tokens: {
    accessToken: JWT,
    idToken: JWT,
    refreshToken: string
  }
}
```

### Auth Operations

#### 1. Check User on Mount
```javascript
const checkUser = useCallback(async () => {
  try {
    const currentUser = await getCurrentUser()
    const session = await fetchAuthSession()
    setUser({...})
  } catch (err) {
    setUser(null)
  } finally {
    setInitializing(false)
  }
}, [])
```

#### 2. Login
```javascript
const login = useCallback(async (usernameOrEmail, password) => {
  // Calls Cognito signIn()
  // Returns { success: true } on success
}, [checkUser])
```

#### 3. Signup
```javascript
const signup = useCallback(async (username, email, password) => {
  // Calls Cognito signUp()
  // Returns confirmation code requirement
}, [])
```

#### 4. Logout
```javascript
const logout = useCallback(async () => {
  setLoading(true)
  try {
    await signOut()  // Cognito sign out
    setUser(null)
    setError(null)
    return { success: true }
  } catch (err) {
    setError(err.message || 'Failed to sign out')
    return { success: false, error: err.message }
  } finally {
    setLoading(false)
  }
}, [])
```

#### 5. Token Refresh
```javascript
const getValidAccessToken = useCallback(async () => {
  const session = await fetchAuthSession({ forceRefresh: false })
  const accessToken = session.tokens.accessToken
  const expiresAt = accessToken.payload.exp * 1000
  const timeUntilExpiry = expiresAt - Date.now()

  // Refresh if expires in less than 5 minutes
  if (timeUntilExpiry < TOKEN_REFRESH_THRESHOLD) {
    const refreshedSession = await fetchAuthSession({ forceRefresh: true })
    return refreshedSession.tokens?.accessToken?.toString() || null
  }

  return accessToken.toString()
}, [])
```

### Global Auth Error Handler

**File**: `/web_client/src/utils/authUtils.js` (lines 136-161)

```javascript
let globalAuthErrorHandler = null

export function setAuthErrorHandler(handler) {
  globalAuthErrorHandler = handler
}

export function handleAuthError() {
  if (globalAuthErrorHandler) {
    globalAuthErrorHandler()
  }
}
```

Registered in App.jsx (lines 41-47):
```javascript
useEffect(() => {
  setAuthErrorHandler(async () => {
    console.warn('🔐 Authentication error detected - logging out user')
    await logout()
  })
}, [logout])
```

---

## Logout Functionality

### Location and Button

**File**: `/web_client/src/components/Header.jsx` (lines 78-82)

```jsx
{user && onLogout && (
  <button className="btn-icon logout-button" onClick={onLogout} title="Logout">
    <LogOut size={18} />
  </button>
)}
```

### Handler Function: `handleLogout()`

**File**: `/web_client/src/App.jsx` (lines 373-404)

```javascript
const handleLogout = async () => {
  if (!window.confirm('Logout?\n\nThis will stop all background requests, close any active sessions, and log you out.')) {
    return
  }

  console.log('🚪 Logging out...')

  try {
    // Always try to stop AgentCore session before logout
    try {
      const agentCoreSessionId = await getAgentCoreSessionId(currentProject)
      const apiClient = createAPIClient(settings.serverUrl, agentCoreSessionId)
      await apiClient.stopAgentCoreSession('DEFAULT')
      console.log('✅ Stopped AgentCore session')
    } catch (error) {
      console.warn('Failed to stop AgentCore session:', error)
      // Continue with logout even if this fails
    }

    // Disconnect from agent session if connected
    if (connected) {
      disconnect()
    }

    // Logout from Cognito
    await logout()
    console.log('✅ Logged out successfully')
  } catch (error) {
    console.error('Failed to logout:', error)
    alert(`Failed to logout: ${error.message}`)
  }
}
```

### Logout Flow Sequence

1. **Confirmation**: User confirms logout via window.confirm()
2. **Stop AgentCore**: Call stopAgentCoreSession() to stop the runtime
3. **Disconnect Session**: Close active agent session if connected
4. **Cognito Logout**: Call Amplify signOut() to clear Cognito session
5. **State Reset**: User state set to null, redirected to login screen

### Post-Logout Behavior

After logout:
- User state cleared (`user = null`)
- UI redirects to Login component
- All local state reset
- LocalStorage settings preserved (for next login)
- Background requests stop

---

## Server Disconnect Flow

### Handler Function: `handleDisconnectServer()`

**File**: `/web_client/src/App.jsx` (lines 406-450)

```javascript
const handleDisconnectServer = async () => {
  if (!serverConnected) {
    console.warn('Server already disconnected')
    return
  }

  if (!window.confirm('Disconnect from server?\n\nThis will stop all background requests and close any active sessions.')) {
    return
  }

  setDisconnecting(true)
  console.log('🛑 Disconnecting from server...')

  try {
    // Disconnect from agent session if connected
    if (connected) {
      disconnect()
    }

    // Set server disconnected flag - this will stop all background requests
    setServerDisconnected(true)

    // Wait 3 seconds for pending invocations to complete
    console.log('⏳ Waiting 3 seconds for pending invocations to complete...')
    await new Promise(resolve => setTimeout(resolve, 3000))

    // Stop AgentCore session after delay
    try {
      const agentCoreSessionId = await getAgentCoreSessionId(currentProject)
      const apiClient = createAPIClient(settings.serverUrl, agentCoreSessionId)
      await apiClient.stopAgentCoreSession('DEFAULT')
      console.log('✅ Stopped AgentCore session')
    } catch (error) {
      console.warn('Failed to stop AgentCore session:', error)
    }

    console.log('✅ Disconnected from server')
  } catch (error) {
    console.error('Failed to disconnect:', error)
    alert(`Failed to disconnect: ${error.message}`)
  } finally {
    setDisconnecting(false)
  }
}
```

### Reconnect Function: `handleReconnectServer()`

**File**: `/web_client/src/App.jsx` (lines 452-455)

```javascript
const handleReconnectServer = () => {
  console.log('🔄 Reconnecting to server...')
  setServerDisconnected(false)
}
```

### Effect of `serverDisconnected` Flag

When `serverDisconnected = true`:
- All API calls pass `disabled={serverDisconnected}` to components
- SessionList, FileBrowser, GitPanel show disabled state
- FilePreview, TerminalPTY show disabled state
- Background health checks stop
- Modal overlay appears with reconnect/force stop options

---

## API Client Configuration

### Environment Variable: `VITE_USE_INVOCATIONS`

**File**: `/web_client/src/api/client.js` (line 13)

```javascript
const USE_INVOCATIONS = import.meta.env.VITE_USE_INVOCATIONS === 'true'
```

Controls which API client is used:
- `true`: InvocationsAPIClient (routes through /invocations)
- `false` (default): DirectAPIClient (direct REST endpoints)

### API Client Factory

```javascript
export function createAPIClient(baseUrl, agentCoreSessionId = null) {
  if (USE_INVOCATIONS) {
    console.log('🔀 Using Invocations API mode')
    return new InvocationsAPIClient(baseUrl, agentCoreSessionId)
  } else {
    console.log('📡 Using Direct API mode')
    return new DirectAPIClient(baseUrl)
  }
}
```

---

## AgentCore Session ID Generation

### Location

**File**: `/web_client/src/utils/authUtils.js` (lines 47-92)

### Function: `getAgentCoreSessionId()`

```javascript
export async function getAgentCoreSessionId(project = null) {
  try {
    const token = await getValidAccessToken()
    if (!token) return null

    // Decode JWT token (without verification - just parse)
    const parts = token.split('.')
    if (parts.length !== 3) return null

    const payload = JSON.parse(atob(parts[1]))
    const userId = payload.sub

    // Check workspace mode from environment variable
    const workspaceMode = import.meta.env.VITE_WORKSPACE_MODE === 'true'

    // Format session ID based on mode
    if (workspaceMode || !project) {
      // Workspace mode: user_id@workspace
      const sessionId = `${userId}@workspace`
      return sessionId
    } else {
      // Project mode: user_id@workspace/project
      const sessionId = `${userId}@workspace/${project}`
      return sessionId
    }
  } catch (error) {
    console.error('Failed to get AgentCore session ID:', error)
    return null
  }
}
```

### Session ID Formats

1. **Workspace Mode** (default): `{user_id}@workspace`
   - Used when `VITE_WORKSPACE_MODE=true`
   - Or when no project is specified

2. **Project Mode**: `{user_id}@workspace/{project}`
   - Used when `VITE_WORKSPACE_MODE=false` and project specified

---

## Adding Logout Functionality

If you need to add logout functionality to other components:

### 1. Import useAuth Hook

```javascript
import { useAuth } from '../hooks/useAuth.jsx'
```

### 2. Get logout function

```javascript
const { logout } = useAuth()
```

### 3. Call logout

```javascript
const handleLogout = async () => {
  await logout()
  // User is redirected to login automatically
}
```

### 4. Alternative: Use App-level handler

Already passes `onLogout` prop to Header:
```javascript
<Header
  onLogout={handleLogout}
  // ... other props
/>
```

---

## State Persistence

### What's Persisted

1. **Settings** (localStorage key: `claude-agent-settings`)
   ```javascript
   {
     serverUrl: string,
     cwd: string,
     model: string,
     backgroundModel: string,
     enableProxy: boolean
   }
   ```

2. **Server Disconnected Flag** (localStorage key: `claude-agent-server-disconnected`)
   ```javascript
   boolean
   ```

### What's NOT Persisted

- User authentication session (Cognito manages this via secure httpOnly cookies)
- Active agent sessions (recreated on app restart)
- Message history (loaded from server on session resume)

---

## Error Handling

### Authentication Errors

All 401 responses trigger global auth error handler:

**File**: `/web_client/src/api/client.js` (lines 18-27)

```javascript
function handleFetchResponse(response) {
  if (response.status === 401) {
    console.error('🔐 Authentication failed - triggering logout')
    handleAuthError()
    const error = new Error('Authentication required')
    error.status = 401
    throw error
  }
  return response
}
```

This is called in every API method to auto-logout on token expiration.

### Cognito Error Mapping

**File**: `/web_client/src/hooks/useAuth.jsx` (lines 87-102)

Maps Cognito error names to user-friendly messages:
- `UserNotFoundException`: User doesn't exist
- `NotAuthorizedException`: Wrong password
- `UserNotConfirmedException`: Email not verified
- `PasswordResetRequiredException`: Password reset needed
- `TooManyRequestsException`: Rate limited

---

## Summary

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| App | App.jsx | Main app, modal, handlers |
| Header | Header.jsx | Logout button |
| AuthProvider | useAuth.jsx | Cognito authentication |
| Auth Utils | authUtils.js | Token, session ID |
| API Client | client.js | stopAgentCoreSession() |

### Key Functions

| Function | File | Purpose |
|----------|------|---------|
| handleLogout | App.jsx | Stop AgentCore + Cognito logout |
| handleDisconnectServer | App.jsx | Disconnect without logout |
| handleForceStopAgentCore | App.jsx | Force stop AgentCore runtime |
| handleReconnectServer | App.jsx | Reconnect to server |
| stopAgentCoreSession | client.js | API call to stop runtime |
| getAgentCoreSessionId | authUtils.js | Extract from JWT |

### State Variables

| State | Type | Purpose |
|-------|------|---------|
| serverDisconnected | boolean | Shows/hides modal |
| user | object\|null | Current user or null |
| connected | boolean | Active agent session |
| disconnecting | boolean | Disconnect in progress |

