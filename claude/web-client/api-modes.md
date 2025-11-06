# API Mode Implementation

This document describes the API abstraction layer in the web client.

## Overview

The web client supports two API modes:

1. **Direct Mode**: Calls REST endpoints directly
2. **Invocations Mode**: Routes all calls through `/invocations` endpoint

## Architecture

```
┌─────────────────────────────────────────┐
│         useClaudeAgent Hook             │
│  (Business logic, state management)     │
└──────────────┬──────────────────────────┘
               │
               │ Uses API Client
               ▼
┌─────────────────────────────────────────┐
│      API Client Abstraction Layer       │
│         (src/api/client.js)             │
└──────────────┬──────────────────────────┘
               │
      ┌────────┴─────────┐
      │                  │
      ▼                  ▼
┌──────────────┐  ┌────────────────────┐
│ Direct Mode  │  │ Invocations Mode   │
│              │  │                    │
│ GET /health  │  │ POST /invocations  │
│ POST /sess.. │  │   {path, method,   │
│ DELETE /..   │  │    payload, ...}   │
└──────────────┘  └────────────────────┘
```

## Implementation Details

### API Client Factory (`createAPIClient`)

```javascript
import { createAPIClient } from '../api/client'

// Automatically creates the right client based on env var
const apiClient = createAPIClient('http://127.0.0.1:8000')
```

### DirectAPIClient

Makes standard REST API calls:

```javascript
// Health check
await apiClient.healthCheck()
// → GET /health

// Create session
await apiClient.createSession({ model: 'claude-3-5-sonnet' })
// → POST /sessions

// Send message
await apiClient.sendMessage(sessionId, 'Hello')
// → POST /sessions/{sessionId}/messages
```

### InvocationsAPIClient

Routes all calls through `/invocations`:

```javascript
// Health check
await apiClient.healthCheck()
// → POST /invocations
//   { path: '/health', method: 'GET' }

// Create session
await apiClient.createSession({ model: 'claude-3-5-sonnet' })
// → POST /invocations
//   { path: '/sessions', method: 'POST', payload: {...} }

// Send message
await apiClient.sendMessage(sessionId, 'Hello')
// → POST /invocations
//   { path: '/sessions/{session_id}/messages',
//     method: 'POST',
//     path_params: { session_id: '...' },
//     payload: { message: 'Hello' } }
```

## Configuration

### Environment Variable

Set in `.env` file:

```bash
# Direct mode (default)
VITE_USE_INVOCATIONS=false

# Invocations mode
VITE_USE_INVOCATIONS=true
```

### Runtime Behavior

The mode is determined at build/startup time:

```javascript
const USE_INVOCATIONS = import.meta.env.VITE_USE_INVOCATIONS === 'true'
```

Console logs indicate active mode:
- 📡 Using Direct API mode
- 🔀 Using Invocations API mode

## API Methods

Both clients implement the same interface:

| Method | Description | Direct Endpoint | Invocations Path |
|--------|-------------|----------------|------------------|
| `healthCheck()` | Check server health | `GET /health` | `/health` |
| `createSession(payload)` | Create new session | `POST /sessions` | `/sessions` |
| `getSessionStatus(id)` | Get session status | `GET /sessions/{id}/status` | `/sessions/{session_id}/status` |
| `getSessionHistory(id)` | Get session history | `GET /sessions/{id}/history` | `/sessions/{session_id}/history` |
| `sendMessage(id, msg)` | Send message | `POST /sessions/{id}/messages` | `/sessions/{session_id}/messages` |
| `respondToPermission(id, reqId, allowed)` | Respond to permission | `POST /sessions/{id}/permissions/respond` | `/sessions/{session_id}/permissions/respond` |
| `deleteSession(id)` | Delete session | `DELETE /sessions/{id}` | `/sessions/{session_id}` |

## Error Handling

Both clients handle errors consistently:

- **404 errors**: Return `{ response: { ok: false, status: 404 }, data: null }`
- **Network errors**: Throw error with descriptive message
- **Server errors**: Throw error with status details

## Testing

### Test Direct Mode

```bash
# Set environment
echo "VITE_USE_INVOCATIONS=false" > web_client/.env

# Start dev server
cd web_client && npm run dev

# Check console for: 📡 Using Direct API mode
```

### Test Invocations Mode

```bash
# Set environment
echo "VITE_USE_INVOCATIONS=true" > web_client/.env

# Start dev server
cd web_client && npm run dev

# Check console for: 🔀 Using Invocations API mode
```

### Verify API Calls

Open browser DevTools → Network tab:

**Direct Mode**: You'll see multiple endpoints
- `/health`
- `/sessions`
- `/sessions/abc123/status`

**Invocations Mode**: You'll only see
- `/invocations` (all calls)

## Benefits

### Direct Mode
✅ Easier debugging (clear endpoint names)
✅ Better for development
✅ Standard REST patterns
✅ Granular monitoring per endpoint

### Invocations Mode
✅ Single entry point
✅ Better for serverless/Lambda
✅ Simplified API gateway configuration
✅ Centralized request logging
✅ Easier to add middleware/auth

## Migration Notes

### From Direct to Invocations

1. Change `.env`: `VITE_USE_INVOCATIONS=true`
2. Restart dev server
3. No code changes needed
4. Test all functionality

### Adding New API Methods

When adding new API calls, implement in both clients:

```javascript
// 1. Add to DirectAPIClient
async newMethod(param) {
  const response = await fetch(`${this.baseUrl}/new-endpoint`, {...})
  return response.json()
}

// 2. Add to InvocationsAPIClient
async newMethod(param) {
  return this._invoke('/new-endpoint', 'POST', { param })
}
```

## Future Enhancements

Potential improvements:

- [ ] Add request/response interceptors
- [ ] Implement retry logic
- [ ] Add request caching
- [ ] Support WebSocket connections
- [ ] Add request timeout configuration
- [ ] Implement request queue for rate limiting
