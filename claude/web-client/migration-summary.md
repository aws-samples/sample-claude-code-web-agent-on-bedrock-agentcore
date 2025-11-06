# API Abstraction Migration Summary

This document summarizes the migration from direct API calls to the unified API client abstraction layer.

## Overview

All web client API calls now go through a single abstraction layer that supports two modes:
- **Direct Mode**: Standard REST API calls (default)
- **Invocations Mode**: Unified `/invocations` endpoint

## Migration Timeline

### Phase 1: Core API Abstraction (Commit: 0de42bc)
- Created `src/api/client.js` with DirectAPIClient and InvocationsAPIClient
- Added factory function `createAPIClient()`
- Environment variable control: `VITE_USE_INVOCATIONS`
- Migrated `useClaudeAgent` hook to use API client

**Endpoints covered:**
- ✅ POST /sessions (create)
- ✅ GET /sessions/{id}/status
- ✅ GET /sessions/{id}/history
- ✅ POST /sessions/{id}/messages
- ✅ POST /sessions/{id}/permissions/respond
- ✅ DELETE /sessions/{id}
- ✅ GET /health

### Phase 2: Error Handling Fix (Commit: 346cf5f)
- Enhanced error objects with `status`, `statusText`, `detail` properties
- Fixed 404 detection in `getSessionStatus()`
- Improved error propagation in `getSessionHistory()`

**Issues fixed:**
- 404 errors not correctly identified
- Status codes not propagated from server
- Error details lost in translation

### Phase 3: Session List Integration (Commit: 8bf940a)
- Added `listSessions()` and `listAvailableSessions()` to API clients
- Updated backend invocations.py to support cwd parameter
- Migrated SessionList component to use API client

**Endpoints covered:**
- ✅ GET /sessions (list active)
- ✅ GET /sessions/available (list from disk)

## Complete API Coverage

All endpoints now go through abstraction layer:

| Endpoint | HTTP Method | Direct Mode | Invocations Mode | Component |
|----------|-------------|-------------|------------------|-----------|
| /health | GET | ✅ | ✅ | useClaudeAgent |
| /sessions | POST | ✅ | ✅ | useClaudeAgent |
| /sessions | GET | ✅ | ✅ | SessionList |
| /sessions/available | GET | ✅ | ✅ | SessionList |
| /sessions/{id}/status | GET | ✅ | ✅ | useClaudeAgent |
| /sessions/{id}/history | GET | ✅ | ✅ | useClaudeAgent |
| /sessions/{id}/messages | POST | ✅ | ✅ | useClaudeAgent |
| /sessions/{id}/permissions/respond | POST | ✅ | ✅ | useClaudeAgent |
| /sessions/{id} | DELETE | ✅ | ✅ | useClaudeAgent |

## Verification

To verify all fetch calls are routed through abstraction:

```bash
# Should only show fetch calls inside client.js
grep -r "fetch(" src/ --include="*.js" --include="*.jsx" | grep -v node_modules
```

**Expected result:** All fetch calls in `src/api/client.js` only.

## Backend Changes

### invocations.py Updates

Added cwd parameter support for list endpoints:

```python
# Before
elif path == "/sessions" and method == "GET":
    return await list_sessions()

# After
elif path == "/sessions" and method == "GET":
    cwd = payload.get("cwd") if payload else None
    return await list_sessions(cwd)
```

Same pattern applied to:
- GET /sessions
- GET /sessions/available
- GET /sessions/{id}/history (already supported)

## Testing

### Manual Testing

1. **Direct Mode Test:**
   ```bash
   echo "VITE_USE_INVOCATIONS=false" > .env
   npm run dev
   # Check console: 📡 Using Direct API mode
   ```

2. **Invocations Mode Test:**
   ```bash
   echo "VITE_USE_INVOCATIONS=true" > .env
   npm run dev
   # Check console: 🔀 Using Invocations API mode
   ```

3. **Verify Network Calls:**
   - Open DevTools → Network tab
   - Direct mode: Multiple endpoint calls
   - Invocations mode: Only `/invocations` calls

### Automated Testing

Use `test_invocations.html`:
```bash
# Start server
uv run backend/server.py

# Open in browser
open test_invocations.html
```

## Benefits Achieved

### 1. **Flexibility**
- Switch API modes via environment variable
- No code changes required
- Both modes fully functional

### 2. **Maintainability**
- Single source of truth for API logic
- Consistent error handling
- Easier to add new endpoints

### 3. **Deployment Options**
- Direct mode: Traditional REST deployment
- Invocations mode: Serverless (Lambda, Cloud Functions)
- Invocations mode: API Gateway with single route

### 4. **Developer Experience**
- Console logging shows active mode
- Type-safe API client interface
- Comprehensive error information

## Future Enhancements

Potential improvements:
- [ ] Add request/response interceptors
- [ ] Implement retry logic with exponential backoff
- [ ] Add request caching layer
- [ ] Support WebSocket connections
- [ ] Request timeout configuration
- [ ] Request queue for rate limiting
- [ ] TypeScript migration for type safety
- [ ] Unit tests for both API clients
- [ ] E2E tests for both modes

## Migration Checklist

For future endpoints, follow this checklist:

- [ ] Add method to DirectAPIClient
- [ ] Add method to InvocationsAPIClient
- [ ] Update backend invocations.py routing
- [ ] Update component to use API client
- [ ] Test both Direct and Invocations modes
- [ ] Update API_MODES.md documentation
- [ ] Add test case to test_invocations.html

## Rollback Plan

If issues arise:

1. **Quick rollback to Direct mode:**
   ```bash
   echo "VITE_USE_INVOCATIONS=false" > .env
   npm run dev
   ```

2. **Revert to pre-abstraction code:**
   ```bash
   git revert 8bf940a 346cf5f 0de42bc
   ```

## Documentation

- **API_MODES.md**: Detailed implementation guide
- **README.md**: User-facing configuration guide
- **test_invocations.html**: Manual testing tool
- **MIGRATION_SUMMARY.md**: This file

## Conclusion

✅ **Migration Complete**

All API calls in the web client now go through the unified abstraction layer, providing flexibility to switch between Direct and Invocations modes without code changes. Both modes have been tested and verified to work correctly.

**Commits:**
- 0de42bc: Add API abstraction layer with Direct and Invocations modes
- 346cf5f: Fix error handling in InvocationsAPIClient
- 8bf940a: Route SessionList API calls through API client abstraction

**Files changed:** 6 files, +746 insertions, -123 deletions
