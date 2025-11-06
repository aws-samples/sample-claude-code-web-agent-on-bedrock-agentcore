# Terminal Implementation Improvement Plan

## Current Implementation Analysis

### Issues Identified

1. **No Real PTY Support**
   - Current implementation uses `asyncio.create_subprocess_shell()` which doesn't allocate a PTY
   - Cannot run interactive applications like `vim`, `nano`, `top`, `htop`, etc.
   - No proper terminal control sequences (cursor movement, screen clearing)
   - Commands are executed independently without persistent shell state

2. **No Session Management**
   - No unique session IDs for terminal sessions
   - Cannot maintain multiple terminal sessions
   - State (environment variables, shell variables) not preserved between commands
   - Current working directory tracking is basic and unreliable

3. **Limited Terminal Emulation**
   - xterm.js on frontend is capable but backend doesn't provide proper PTY
   - No support for terminal resize events
   - No proper handling of special keys (Ctrl+C, Ctrl+D, etc.)

4. **Architecture Limitations**
   - Streaming output via HTTP works but doesn't support bidirectional communication needed for interactive apps
   - No way to send input to running processes

## Proposed Solution (HTTP-Only, No WebSocket)

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (xterm.js)                   │
│  - Display terminal UI                                       │
│  - Capture user input                                        │
│  - HTTP polling for output                                   │
│  - HTTP POST for input                                       │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP REST API
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         PTY Session Manager                         │    │
│  │  - Create/Resume/Close sessions with UUID          │    │
│  │  - Track active PTY processes                       │    │
│  │  - Session timeout management                       │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         PTY Process (per session)                   │    │
│  │  - Real PTY allocated via pty.fork() or similar    │    │
│  │  - Running shell (bash/zsh) with persistent state  │    │
│  │  - Output buffer for HTTP polling                   │    │
│  │  - Input queue for commands                         │    │
│  └────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Backend: PTY Session Manager

**Technology Choice: `pexpect` library**
- Pure Python, no external dependencies beyond standard pty module
- Good support for PTY operations
- Works well with asyncio
- Can handle terminal resizing

Alternative option: Direct `pty` module usage for more control

**Session Structure:**
```python
class PTYSession:
    session_id: str  # UUID
    process: pexpect.spawn  # PTY process
    output_buffer: deque  # Recent output for polling
    created_at: datetime
    last_activity: datetime
    rows: int  # Terminal size
    cols: int
    cwd: str  # Current working directory
```

#### 2. HTTP API Endpoints (No WebSocket)

**POST /terminal/sessions**
- Create new PTY session
- Start shell process (bash/zsh)
- Return session_id
- Request body: `{rows, cols, cwd, shell_type}`

**GET /terminal/sessions/{session_id}/output**
- Poll for new output since last read
- Uses sequence number or timestamp for efficient polling
- Returns: `{output: string, seq: number, exit_code: int|null}`
- Client polls every 100-200ms

**POST /terminal/sessions/{session_id}/input**
- Send user input to PTY
- Request body: `{data: string}`
- Handles special keys encoded as escape sequences

**POST /terminal/sessions/{session_id}/resize**
- Update terminal size
- Request body: `{rows, cols}`
- Calls `setwinsize()` on PTY

**DELETE /terminal/sessions/{session_id}**
- Close PTY session
- Kill process gracefully (SIGTERM then SIGKILL)
- Clean up resources

**GET /terminal/sessions**
- List all active sessions
- Returns session metadata

**GET /terminal/sessions/{session_id}/status**
- Get session info (alive, exit_code, etc.)

#### 3. Frontend: Enhanced xterm.js Integration

**Polling Strategy:**
```javascript
// Start polling loop
const pollInterval = 100 // ms
setInterval(async () => {
  const data = await fetch(`/terminal/sessions/${sessionId}/output`)
  const json = await data.json()
  if (json.output) {
    terminal.write(json.output)
  }
}, pollInterval)
```

**Input Handling:**
```javascript
terminal.onData(async (data) => {
  await fetch(`/terminal/sessions/${sessionId}/input`, {
    method: 'POST',
    body: JSON.stringify({ data })
  })
})
```

**Terminal Resize:**
```javascript
fitAddon.fit()
const { rows, cols } = terminal
await fetch(`/terminal/sessions/${sessionId}/resize`, {
  method: 'POST',
  body: JSON.stringify({ rows, cols })
})
```

### Implementation Benefits

1. **Full Interactive Support**
   - Run vim, nano, top, htop, ssh, etc.
   - Proper terminal control sequences
   - Real shell with persistent state

2. **Session Management**
   - Multiple independent terminal sessions
   - Session resumption after disconnect
   - Auto-cleanup of inactive sessions

3. **HTTP-Only Architecture**
   - No WebSocket dependency
   - Works through HTTP proxies and load balancers
   - Simple polling mechanism with good performance (100-200ms latency acceptable for terminal)

4. **Better User Experience**
   - Native terminal behavior
   - Full terminal capabilities
   - Proper signal handling (Ctrl+C, Ctrl+Z, etc.)

### Implementation Plan

#### Phase 1: Backend PTY Foundation
1. Add `pexpect` dependency to `pyproject.toml`
2. Create `backend/core/pty_session.py` - PTY session class
3. Create `backend/core/pty_manager.py` - Session manager
4. Create `backend/api/terminal.py` - REST endpoints
5. Add session cleanup task (remove idle sessions after 30min)

#### Phase 2: Frontend Integration
1. Create new `Terminal.jsx` component with session management
2. Implement output polling mechanism
3. Implement input forwarding
4. Add terminal resize handling
5. Add session lifecycle (create on open, close on unmount)

#### Phase 3: Testing & Polish
1. Test with various interactive applications (vim, nano, htop)
2. Test session resumption
3. Test multiple simultaneous sessions
4. Add error handling and recovery
5. Performance optimization (buffer management, polling interval tuning)

### Code Structure

```
backend/
├── api/
│   └── terminal.py          # REST API endpoints
├── core/
│   ├── pty_session.py       # PTY session class
│   └── pty_manager.py       # Session manager
└── server.py                # Register terminal router

web_client/
└── src/
    └── components/
        └── Terminal.jsx     # Enhanced terminal component
```

### Libraries to Use

**Backend:**
- `pexpect` - PTY and spawn management (recommended)
  - Alternative: `ptyprocess` (lower-level)
- `asyncio` - Async I/O for non-blocking operations

**Frontend:**
- `xterm` - Already installed (v5.3.0)
- `xterm-addon-fit` - Already installed
- Optional: `xterm-addon-web-links` - Clickable URLs

### Performance Considerations

1. **Polling Interval:** 100-200ms provides good balance
   - Lower = more responsive but higher server load
   - Higher = less load but more latency

2. **Output Buffering:** Keep last 10000 lines in memory per session
   - Prevents memory leaks from runaway output
   - Old output discarded using `deque(maxlen=10000)`

3. **Session Timeout:** Auto-close after 30min inactivity
   - Prevents resource leaks from abandoned sessions
   - Configurable per deployment

4. **Concurrent Sessions:** Limit to 10-20 per user
   - Prevents abuse
   - Protects server resources

### Security Considerations

1. **Authentication:** Tie sessions to user authentication
2. **Command Restrictions:** Optional command filtering/logging
3. **Resource Limits:** CPU/memory limits per session
4. **Audit Logging:** Log all terminal commands for security review
5. **Session Isolation:** Separate user workspaces

### Migration Path

1. Keep existing simple shell API (`/shell/execute`) for backward compatibility
2. Add new PTY-based terminal API (`/terminal/*`)
3. Update web client to use new PTY API
4. Eventually deprecate old shell API if not needed

## Example API Usage

### Create Session
```bash
curl -X POST http://localhost:8000/terminal/sessions \
  -H "Content-Type: application/json" \
  -d '{"rows": 24, "cols": 80, "cwd": "/workspace", "shell": "bash"}'

# Response: {"session_id": "uuid-here", "status": "running"}
```

### Send Input
```bash
curl -X POST http://localhost:8000/terminal/sessions/UUID/input \
  -H "Content-Type: application/json" \
  -d '{"data": "ls -la\n"}'
```

### Poll Output
```bash
curl http://localhost:8000/terminal/sessions/UUID/output?seq=0

# Response: {"output": "...", "seq": 42, "exit_code": null}
```

### Resize Terminal
```bash
curl -X POST http://localhost:8000/terminal/sessions/UUID/resize \
  -H "Content-Type: application/json" \
  -d '{"rows": 40, "cols": 120}'
```

### Close Session
```bash
curl -X DELETE http://localhost:8000/terminal/sessions/UUID
```

## Next Steps

1. Review and approve this design
2. Implement Phase 1 (backend PTY foundation)
3. Test backend independently with curl
4. Implement Phase 2 (frontend integration)
5. End-to-end testing with vim, htop, etc.
6. Documentation and deployment

## References

- **pexpect documentation**: https://pexpect.readthedocs.io/
- **xterm.js documentation**: https://xtermjs.org/
- **PTY in Python**: https://docs.python.org/3/library/pty.html
- **Similar implementations:**
  - wetty (Node.js, uses WebSocket but good reference)
  - ttyd (C, WebSocket-based)
  - Our approach: HTTP polling instead of WebSocket for better compatibility
