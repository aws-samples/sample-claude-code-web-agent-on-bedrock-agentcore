# OAuth 3-Legged (3LO) Authentication Flow

This document describes the GitHub OAuth 3-legged authentication flow implementation for the Claude Agent API Server.

## Overview

The 3LO (3-legged OAuth) flow allows users to authenticate with external OAuth providers (like GitHub) through a browser-based authorization flow. This is useful when the user needs to explicitly grant permissions to access their external resources.

## Flow Diagram

```
User → Web Client → Backend → AgentCore Identity → GitHub → User Browser
  ↓                                                            ↓
  └────────────────────── Callback ←──────────────────────────┘
```

## Detailed Flow

### 1. Initial Token Request

**Web Client** calls backend endpoint:
```
POST /oauth/github/token
Headers:
  Authorization: Bearer <user-jwt-token>
  X-Amzn-Bedrock-AgentCore-Runtime-Workload-AccessToken: <workload-token>
```

**Backend** (`backend/api/oauth.py::get_github_oauth_token()`):
- Extracts `user_id` from JWT token
- Calls AgentCore's `get_resource_oauth2_token()`:
  ```python
  response = client.get_resource_oauth2_token(
      workloadIdentityToken=workload_token,
      resourceCredentialProviderName="github-provider",
      scopes=["repo", "read:user"],
      oauth2Flow="USER_FEDERATION",
      sessionUri=f"urn:ietf:params:oauth:request_uri:{user_id}",
      forceAuthentication=False
  )
  ```

**Response scenarios**:

**A. Token already exists (user previously authorized)**:
```json
{
  "access_token": "gho_xxxx",
  "token_type": "Bearer",
  "session_uri": "urn:ietf:params:oauth:request_uri:user-123",
  "session_status": "COMPLETED",
  "gh_auth": {
    "status": "success",
    "message": "GitHub CLI authenticated successfully"
  }
}
```

**B. Authorization required**:
```json
{
  "authorization_url": "https://github.com/login/oauth/authorize?client_id=...",
  "token_type": "Bearer",
  "session_uri": "urn:ietf:params:oauth:request_uri:user-123",
  "session_status": "IN_PROGRESS"
}
```

### 2. User Authorization (Scenario B)

**Web Client** (`web_client/src/App.jsx::handleGithubAuth()`):
- Detects `authorization_url` in response
- Opens URL in new browser window:
  ```javascript
  window.open(result.authorization_url, '_blank')
  ```

**User actions**:
1. Browser opens GitHub authorization page
2. User reviews permissions requested
3. User clicks "Authorize" button

**GitHub**:
- Redirects to callback URL configured in AgentCore:
  ```
  http://localhost:8080/oauth/callback?session_id=urn:ietf:params:oauth:request_uri:user-123
  ```

### 3. Callback Handling

**Web Client Router** (`web_client/src/main.jsx`):
- Route `/oauth/callback` → `OAuthCallback` component

**OAuthCallback Component** (`web_client/src/components/OAuthCallback.jsx`):
```javascript
// Extract session_id from URL
const urlParams = new URLSearchParams(window.location.search)
const sessionId = urlParams.get('session_id')

// Call backend callback endpoint
const response = await fetch(
  `${serverUrl}/oauth/github/callback?session_id=${sessionId}`,
  {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${user.token}`,
      'Content-Type': 'application/json'
    }
  }
)
```

**Backend** (`backend/api/oauth.py::github_oauth_callback()`):
```python
# Extract user_id from JWT token
user_id = extract_user_from_jwt(request.headers["authorization"])

# Complete the OAuth flow
client = get_bedrock_agentcore_client()
response = client.complete_resource_token_auth(
    sessionUri=session_id,
    userIdentifier={"userToken": token}
)
```

**Response**:
- Returns HTML success page with "Close Window" button
- Auto-closes after 2 seconds

### 4. Using the Token

After successful authorization, subsequent calls to `/oauth/github/token` will return the `access_token` directly without requiring re-authorization (until token expires or is revoked).

## Endpoints

### POST /oauth/github/token

**Purpose**: Request GitHub OAuth token or initiate authorization flow

**Request**:
```http
POST /oauth/github/token
Authorization: Bearer <jwt-token>
X-Amzn-Bedrock-AgentCore-Runtime-Workload-AccessToken: <workload-token>
Content-Type: application/json
```

**Response (Success - Token Available)**:
```json
{
  "access_token": "gho_xxxxxxxxxxxx",
  "token_type": "Bearer",
  "session_uri": "urn:ietf:params:oauth:request_uri:user-123",
  "session_status": "COMPLETED",
  "gh_auth": {
    "status": "success",
    "message": "GitHub CLI authenticated successfully"
  }
}
```

**Response (Authorization Required)**:
```json
{
  "authorization_url": "https://github.com/login/oauth/authorize?client_id=...",
  "token_type": "Bearer",
  "session_uri": "urn:ietf:params:oauth:request_uri:user-123",
  "session_status": "IN_PROGRESS"
}
```

### GET /oauth/github/callback

**Purpose**: Complete OAuth flow after user authorization

**Request**:
```http
GET /oauth/github/callback?session_id=urn:ietf:params:oauth:request_uri:user-123
Authorization: Bearer <jwt-token>
```

**Response**:
- HTML page with success message
- Auto-close functionality

## Configuration

### AgentCore Identity Configuration

The OAuth provider must be configured in AgentCore Identity:

1. **Resource Credential Provider Name**: `github-provider`
2. **OAuth Scopes**: `["repo", "read:user"]`
3. **Callback URL**: `http://localhost:8080/oauth/callback` (or production URL)
4. **OAuth Flow Type**: `USER_FEDERATION`

### Web Client Configuration

Callback URL must match the web client's base URL:
- Development: `http://localhost:8080/oauth/callback`
- Production: `https://your-domain.com/oauth/callback`

### Backend Server Configuration

Set the `OAUTH_CALLBACK_URL` environment variable before starting the backend server:

```bash
# Development
export OAUTH_CALLBACK_URL="http://localhost:8080/oauth/callback"
./serve

# Production (example with AgentCore)
export OAUTH_CALLBACK_URL="https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/arn%3Aaws%3A.../oauth/callback"
uv run uvicorn backend.server:app --host 0.0.0.0 --port 8080
```

**Default behavior**: If `OAUTH_CALLBACK_URL` is not set, the backend defaults to `http://localhost:8080/oauth/callback` with a warning logged.

**How it works**: The backend passes this URL to AgentCore's `get_resource_oauth2_token()` API as the `resourceOauth2ReturnUrl` parameter. AgentCore uses this URL when redirecting the user back after OAuth authorization.

## Security Considerations

1. **JWT Token Validation**: Backend extracts `user_id` from JWT token without signature verification (assumes token validated by API gateway)

2. **Session Binding**: OAuth sessions are bound to user via `sessionUri` containing `user_id`

3. **Token Storage**: Access tokens are managed by AgentCore Identity, not stored in web client

4. **CORS**: Callback endpoint must allow requests from web client origin

## Error Handling

### Missing Workload Token
```json
{
  "detail": "Missing x-amzn-bedrock-agentcore-runtime-workload-accesstoken header"
}
```

### Invalid JWT Token
```json
{
  "detail": "Missing or invalid Authorization header (user_id not found in JWT)"
}
```

### Authorization Failed
```json
{
  "session_status": "FAILED",
  "authorization_url": null,
  "access_token": null
}
```

### Callback Error
```json
{
  "detail": "Failed to complete OAuth flow: ValidationException - ..."
}
```

## Testing

### Manual Test Flow

1. **Start Backend Server**:
   ```bash
   ./serve
   ```

2. **Start Web Client**:
   ```bash
   cd web_client
   npm run dev
   ```

3. **Trigger OAuth Flow**:
   - Log in to web client
   - Click GitHub icon in header
   - If not authorized: browser opens GitHub authorization page
   - Authorize access on GitHub
   - Browser redirects to callback page
   - Callback page shows success and auto-closes
   - Main window now has valid OAuth token

4. **Verify Token**:
   - Click GitHub icon again
   - Should show "GitHub authentication successful!" immediately (no redirect)

### Test via CLI

```bash
# Set environment variables
export TOKEN="your-jwt-token"
export WORKLOAD_IDENTITY_TOKEN="your-workload-token"

# Test token request
uv run temp/test_github_oauth.py

# Expected output:
# - First run: authorization_url returned
# - After authorizing in browser: access_token returned
```

## References

- AWS Bedrock AgentCore Identity API: `get_resource_oauth2_token()`
- AWS Bedrock AgentCore Identity API: `complete_resource_token_auth()`
- Reference implementation: `amazon-bedrock-agentcore-samples/oauth2_callback_server.py`

## Implementation Files

- Backend OAuth endpoint: `backend/api/oauth.py`
- Invocations routing: `backend/api/invocations.py`
- Web client callback component: `web_client/src/components/OAuthCallback.jsx`
- Web client routing: `web_client/src/main.jsx`
- Test script: `temp/test_github_oauth.py`
