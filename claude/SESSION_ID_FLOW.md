# Session ID Flow

This document explains how session IDs are managed across the system, from creation to SDK persistence.

## Problem Statement

The Claude Agent SDK generates its own internal session_id after the first message is processed. However, the backend needs to track sessions immediately upon creation, before any messages are sent. This creates a mismatch between:

1. **Backend's temporary ID**: UUID generated when session is created
2. **SDK's real ID**: Generated after first message processing

## Solution Overview

We use a two-phase session ID lifecycle:

1. **Phase 1 - Creation**: Backend generates UUID, stores session under UUID key
2. **Phase 2 - First Message**: SDK generates real ID, backend updates dictionary key, frontend updates state

## Detailed Flow

### 1. Session Creation

**Client** (`web_client/src/hooks/useClaudeAgent.js:186-216`):
```javascript
const data = await apiClientRef.current.createSession(payload)
setSessionId(data.session_id)  // Stores UUID (e.g., "abc-123-def")
```

**Backend** (`backend/api/sessions.py:43-61`):
```python
internal_session_id = await manager.create_session(...)
# Returns UUID for new sessions, actual ID for resumed sessions
return CreateSessionResponse(session_id=internal_session_id)
```

**SessionManager** (`backend/core/session_manager.py:34-88`):
```python
session_id = resume_session_id or str(__import__("uuid").uuid4())
# Stores in dictionary: self.sessions[session_id] = session
```

**Result**: Client has UUID that matches backend's dictionary key.

### 2. First Message Sent

**Client** (`web_client/src/hooks/useClaudeAgent.js:265-415`):
```javascript
// sessionId is UUID from creation
const eventSource = await apiClientRef.current.sendMessageStream(sessionId, message)
```

**Backend** (`backend/api/messages.py`):
```python
# Looks up session by UUID - works correctly!
session = manager.get_session(session_id)
```

### 3. SDK Processes Message

**Backend** (`backend/core/session.py:476-489`):
```python
elif isinstance(msg, ResultMessage):
    # Extract real session_id from SDK's ResultMessage
    real_session_id = msg.session_id if hasattr(msg, 'session_id') else self.session_id

    # Update SessionManager if we got a different session_id from SDK
    if real_session_id != self.session_id:
        session_manager.update_session_id(self.session_id, real_session_id)

    yield {
        "type": "result",
        "session_id": real_session_id
    }
```

**SessionManager** (`backend/core/session_manager.py:107-129`):
```python
def update_session_id(self, old_session_id: str, new_session_id: str):
    # Move session from UUID key to real SDK session_id key
    session = self.sessions.pop(old_session_id)
    session.session_id = new_session_id
    self.sessions[new_session_id] = session
    print(f"[SessionManager] Updated session ID: {old_session_id} → {new_session_id}")
```

### 4. Frontend Updates

**Client** (`web_client/src/hooks/useClaudeAgent.js:366-385`):
```javascript
case 'result':
  // Update session_id if we got real session_id from SDK
  if (data.session_id && data.session_id !== sessionId) {
    console.log(`🔄 Updating session ID from temporary to real: ${sessionId} → ${data.session_id}`)
    setSessionId(data.session_id)
  }
  break

case 'done':
  // Also check in done event (backup)
  if (data.session_id && data.session_id !== sessionId) {
    console.log(`🔄 Updating session ID from temporary to real: ${sessionId} → ${data.session_id}`)
    setSessionId(data.session_id)
  }
  break
```

**Result**: Both backend and frontend now use real SDK session_id.

## State Transitions

```
Backend SessionManager Dictionary:
  sessions[UUID] = AgentSession
    ↓ (after first message)
  sessions[REAL_ID] = AgentSession (same object)

Frontend sessionId State:
  sessionId = UUID
    ↓ (after first message result)
  sessionId = REAL_ID

Session Object's session_id Field:
  session.session_id = UUID
    ↓ (in update_session_id)
  session.session_id = REAL_ID
```

## Key Benefits

1. **Immediate Usability**: Client can send messages immediately after session creation
2. **Correct Routing**: All API calls work because UUID exists in SessionManager dictionary
3. **Seamless Transition**: Both backend and frontend update to real ID automatically
4. **No Race Conditions**: Backend updates before sending result to frontend
5. **Proper Cleanup**: Disconnect/delete work with both UUID and real ID

## Edge Cases Handled

### Case 1: Disconnect Before First Message

**Scenario**: User creates session, then disconnects before sending any messages.

**Behavior**:
- Client calls `deleteSession(UUID)`
- Backend looks up `sessions[UUID]` - **Found!**
- Session cleaned up successfully

### Case 2: Multiple Messages Before ID Update

**Scenario**: Client sends multiple messages in quick succession.

**Behavior**:
- First message triggers SessionManager update
- Subsequent messages use real ID (if update completed)
- Or use UUID (if update not yet completed) - still works because SessionManager has both keys during transition

### Case 3: Resume Existing Session

**Scenario**: User resumes a session that was previously created.

**Behavior**:
- `create_session()` receives `resume_session_id` parameter
- Backend returns actual session_id (not UUID)
- No ID update needed - session_id is already correct

### Case 4: Session List Before SDK Persistence

**Scenario**: User creates session, SDK hasn't written `.jsonl` file yet.

**Behavior**:
- `list_available_sessions()` checks in-memory sessions first
- Finds session with UUID in `self.sessions` dictionary
- Returns it with `"active": true` flag
- After SDK persists, it appears from disk with real ID

## Related Code Locations

### Backend

- **Session Creation**: `backend/api/sessions.py:33-61`
- **Session Manager**: `backend/core/session_manager.py:107-129`
- **Message Streaming**: `backend/core/session.py:476-495`
- **ID Update Logic**: `backend/core/session_manager.py:107-129`

### Frontend

- **Session Creation**: `web_client/src/hooks/useClaudeAgent.js:162-217`
- **Message Sending**: `web_client/src/hooks/useClaudeAgent.js:265-415`
- **ID Update Logic**: `web_client/src/hooks/useClaudeAgent.js:366-385`

## Debugging

### Backend Logs

```
[Session] Creating session abc-123-def
[SessionManager] Session abc-123-def created
[SessionManager] Updated session ID: abc-123-def → real-sdk-id-456
```

### Frontend Logs

```
🆔 Generated Agent Core Session ID: user123@workspace
🔗 Connecting with Agent Core Session ID: user123@workspace
✅ Connected to Claude Agent
Session ID: abc-123-def

🚀 Stream started
🔄 Updating session ID from temporary to real: abc-123-def → real-sdk-id-456
✅ Stream completed
```

## Migration Notes

### Previous Implementation (Broken)

- Backend returned `"new_session"` placeholder
- Client stored `"new_session"` in state
- `sendMessage("new_session")` → 404 error (not in SessionManager)
- Disconnect/delete failed with 404

### Current Implementation (Fixed)

- Backend returns UUID (temporary session ID)
- Client stores UUID in state
- `sendMessage(UUID)` → Works! (UUID is in SessionManager)
- After first message, both sides update to real ID
- Disconnect/delete work correctly

## Testing Checklist

- [ ] Create new session → Returns UUID
- [ ] Send first message with UUID → Succeeds
- [ ] Backend logs show ID update: UUID → real ID
- [ ] Frontend logs show ID update: UUID → real ID
- [ ] Second message uses real ID → Succeeds
- [ ] Disconnect/delete works before first message
- [ ] Disconnect/delete works after first message
- [ ] Resume session → Returns actual ID (not UUID)
- [ ] Session appears in list immediately after creation
- [ ] Session still appears after SDK persists to disk
