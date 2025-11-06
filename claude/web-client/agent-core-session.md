# Agent Core Session ID Implementation

This document describes the implementation of Agent Core Session ID headers for all invocations API calls in the web client.

## Overview

All invocations API requests now include the `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` header, which uniquely identifies each web client session. This follows the same pattern used in the CLI shell client.

## Implementation Details

### 1. Session ID Generation (`src/utils/sessionUtils.js`)

A utility module provides functions for generating and validating agent core session IDs:

```javascript
generateAgentCoreSessionId()  // Returns: "web-session-{uuid}"
isValidAgentCoreSessionId(id) // Validates format
```

**Format**: `web-session-{uuid}`
- Prefix: `web-session-` (distinguishes web client sessions)
- UUID: Standard UUID v4 (36 characters)
- Total length: ~48 characters

**Example**: `web-session-f47ac10b-58cc-4372-a567-0e02b2c3d479`

### 2. API Client Updates (`src/api/client.js`)

#### InvocationsAPIClient Class

The `InvocationsAPIClient` class has been enhanced to support agent core session IDs:

**Constructor**:
```javascript
constructor(baseUrl, agentCoreSessionId = null)
```

**New Method**:
```javascript
setAgentCoreSessionId(sessionId)  // Update session ID after creation
```

**Header Injection**:
- The `_invoke()` method automatically adds the header if session ID is set
- The `executeShellCommand()` method also includes the header for streaming responses

**Header Name**: `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id`

#### DirectAPIClient Class

The `DirectAPIClient` remains unchanged as it uses direct REST endpoints that don't require agent core session IDs.

#### Factory Function

The `createAPIClient()` factory has been updated:

```javascript
createAPIClient(baseUrl, agentCoreSessionId = null)
```

- Returns `InvocationsAPIClient` with session ID when `USE_INVOCATIONS=true`
- Returns `DirectAPIClient` (no session ID) when `USE_INVOCATIONS=false`

### 3. Hook Integration (`src/hooks/useClaudeAgent.js`)

The `useClaudeAgent` hook manages the agent core session ID lifecycle:

**Session ID Generation**:
- Generated once when connecting to server (`connect()`)
- Generated when loading existing sessions (`loadSession()`)
- Persisted for the duration of the web client session
- Reused across multiple Claude Agent sessions

**Storage**:
```javascript
const agentCoreSessionIdRef = useRef(null)
```

**Lifecycle**:
1. **First Connection**: Generate new session ID
2. **Session Switch**: Keep same session ID (represents the web browser session)
3. **Page Reload**: New session ID generated (new web session)

## When Headers Are Sent

The `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` header is included in:

### All Invocations API Calls

✅ **Session Operations**:
- `POST /invocations` → `/sessions` (create)
- `POST /invocations` → `/sessions/{id}/status` (status)
- `POST /invocations` → `/sessions/{id}/history` (history)
- `POST /invocations` → `/sessions/{id}` (delete)
- `POST /invocations` → `/sessions` (list)
- `POST /invocations` → `/sessions/available` (list available)

✅ **Message Operations**:
- `POST /invocations` → `/sessions/{id}/messages` (send)
- `POST /invocations` → `/sessions/{id}/permissions/respond` (permissions)

✅ **File Operations**:
- `POST /invocations` → `/files` (list)
- `POST /invocations` → `/files/info` (info)
- `POST /invocations` → `/files/save` (save)

✅ **Shell Operations**:
- `POST /invocations` → `/shell/execute` (execute - streaming)
- `POST /invocations` → `/shell/cwd` (get/set cwd)

### Direct API Mode

❌ **Not included** in direct API mode (when `VITE_USE_INVOCATIONS=false`)

## Header Format

```http
POST /invocations HTTP/1.1
Host: api.example.com
Content-Type: application/json
Authorization: Bearer {access-token}
X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: web-session-f47ac10b-58cc-4372-a567-0e02b2c3d479

{
  "path": "/sessions",
  "method": "POST",
  "payload": {
    "model": "claude-3-5-sonnet-20241022"
  }
}
```

## Comparison with CLI Client

### Similarities

Both web client and CLI shell client follow the same pattern:

| Aspect | Web Client | CLI Shell Client |
|--------|-----------|------------------|
| Header Name | `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` | `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` |
| Format | `web-session-{uuid}` | `shell-session-{uuid}` |
| UUID Version | v4 (crypto.randomUUID) | v4 (uuid.uuid4) |
| Lifecycle | Per web browser session | Per shell process |
| Applied To | All invocations calls | All AgentCore calls |

### Differences

| Aspect | Web Client | CLI Shell Client |
|--------|-----------|------------------|
| Prefix | `web-session-` | `shell-session-` |
| Language | JavaScript | Python |
| Persistence | In-memory (React ref) | Instance variable |
| Generation | On connect/load | On __init__ |

## Configuration

### Enable Invocations Mode

Set environment variable in `.env`:

```bash
VITE_USE_INVOCATIONS=true
```

### Environment Variables

```bash
# Enable invocations API mode
VITE_USE_INVOCATIONS=true

# AWS Cognito configuration (for authentication)
VITE_COGNITO_USER_POOL_ID=us-west-2_xxxxxxxxx
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
VITE_COGNITO_REGION=us-west-2
```

## Backend Requirements

The backend server (when proxying to AWS Bedrock AgentCore) should:

1. **Accept the header**: Read `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` from requests
2. **Forward to AgentCore**: Include header when calling AgentCore runtime
3. **Validate format**: Ensure session ID is valid (40+ chars, contains UUID)
4. **Log session ID**: For debugging and tracing requests

Example backend validation:

```python
def validate_agent_core_session_id(session_id: str) -> bool:
    """Validate agent core session ID format."""
    if not session_id or len(session_id) < 40:
        return False
    if not ('-' in session_id and session_id.count('-') >= 4):
        return False
    return True
```

## Debugging

### Console Logs

When invocations mode is enabled, you'll see:

```
🔀 Using Invocations API mode
🆔 Agent Core Session ID: web-session-f47ac10b-58cc-4372-a567-0e02b2c3d479
🆔 Generated Agent Core Session ID: web-session-f47ac10b-58cc-4372-a567-0e02b2c3d479
```

### Network Inspector

Check request headers in browser DevTools:

1. Open DevTools (F12)
2. Go to Network tab
3. Find POST request to `/invocations`
4. Check Request Headers
5. Look for `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id`

### Verify Header is Present

```javascript
// In browser console
performance.getEntriesByType('resource')
  .filter(r => r.name.includes('invocations'))
  .forEach(r => console.log(r.name))
```

## Troubleshooting

### Header Not Sent

**Problem**: `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` header is missing

**Solutions**:
1. Verify `VITE_USE_INVOCATIONS=true` in `.env`
2. Rebuild the app: `npm run build`
3. Check console for "Using Invocations API mode" message
4. Ensure API client is created with session ID

### Invalid Session ID Format

**Problem**: Session ID doesn't match expected format

**Solutions**:
1. Check `sessionUtils.js` UUID generation
2. Verify browser supports `crypto.randomUUID()`
3. Check console logs for generated session ID
4. Validate format: `prefix-uuid` (48 chars)

### Session ID Not Persisted

**Problem**: Session ID changes between requests

**Solutions**:
1. Verify `useRef` is being used (not `useState`)
2. Check that API client is reused, not recreated
3. Ensure session ID is set before first request

## Testing

### Unit Tests

Test session ID generation:

```javascript
import { generateAgentCoreSessionId, isValidAgentCoreSessionId } from './sessionUtils'

test('generates valid session ID', () => {
  const sessionId = generateAgentCoreSessionId()
  expect(sessionId).toMatch(/^web-session-[0-9a-f-]{36}$/)
  expect(isValidAgentCoreSessionId(sessionId)).toBe(true)
})
```

### Integration Tests

Verify header is sent:

```javascript
// Mock fetch and check headers
const mockFetch = jest.fn()
global.fetch = mockFetch

const client = createAPIClient('http://localhost:8000', 'test-session-123')
await client.healthCheck()

expect(mockFetch).toHaveBeenCalledWith(
  expect.anything(),
  expect.objectContaining({
    headers: expect.objectContaining({
      'X-Amzn-Bedrock-AgentCore-Runtime-Session-Id': 'test-session-123'
    })
  })
)
```

## References

- CLI Shell Client: `cli_client/shell_client.py` (line 127)
- Web Client API: `web_client/src/api/client.js`
- Session Utils: `web_client/src/utils/sessionUtils.js`
- Hook Integration: `web_client/src/hooks/useClaudeAgent.js`

## Related Documentation

- [Authentication Implementation](./AUTH_IMPLEMENTATION.md)
- [API Modes](./API_MODES.md)
- [API Client Documentation](./README.md)
