# Web Client Environment Variables Configuration

This document describes all environment variables that can be configured for the web client.

## Configuration File

The web client uses environment variables defined in `web_client/.env`. A template file `web_client/.env.example` is provided for reference.

## Available Environment Variables

### API Mode Configuration

#### `VITE_USE_INVOCATIONS`
- **Type**: Boolean (`'true'` or `'false'`)
- **Default**: `'true'`
- **Description**: Set to `'true'` to use unified `/invocations` endpoint, `'false'` for direct REST API
- **Usage**: Controls which API pattern the client uses to communicate with the backend

### Terminal Output Mode

#### `VITE_TERMINAL_USE_STREAMING`
- **Type**: Boolean (`'true'` or `'false'`)
- **Default**: `'true'`
- **Description**: Set to `'true'` for SSE streaming (HTTP/2), `'false'` for HTTP polling
- **Usage**: Controls how terminal output is fetched from the server

### AWS Cognito Configuration

#### `VITE_COGNITO_REGION`
- **Type**: String
- **Required**: Yes (if using Cognito authentication)
- **Example**: `us-west-2`
- **Description**: AWS region where your Cognito User Pool is located

#### `VITE_COGNITO_USER_POOL_ID`
- **Type**: String
- **Required**: Yes (if using Cognito authentication)
- **Example**: `us-west-2_Sw8yyFfBT`
- **Description**: Your Cognito User Pool ID
- **How to find**: AWS Console → Cognito → User Pools → [Your Pool] → Pool ID

#### `VITE_COGNITO_CLIENT_ID`
- **Type**: String
- **Required**: Yes (if using Cognito authentication)
- **Example**: `2d2cqqjvpf1ecqjg6gh1u6fivl`
- **Description**: Your Cognito App Client ID
- **How to find**: AWS Console → Cognito → User Pools → [Your Pool] → App clients

#### `VITE_COGNITO_OAUTH_DOMAIN` (Optional)
- **Type**: String
- **Required**: No
- **Example**: `your-domain.auth.us-west-2.amazoncognito.com`
- **Description**: Cognito OAuth domain for hosted UI (if using OAuth flows)

### Default Settings

These settings control the default values in the UI. Users can override them in the Settings modal.

#### `VITE_DEFAULT_SERVER_URL`
- **Type**: String (URL)
- **Default**: `http://127.0.0.1:8000`
- **Description**: Default backend API server URL
- **Examples**:
  - Local development: `http://127.0.0.1:8000`
  - Docker: `http://localhost:8080`
  - Production: `https://api.example.com`

#### `VITE_DEFAULT_CWD`
- **Type**: String (path)
- **Default**: `/workspace`
- **Description**: Default working directory for agent sessions
- **Examples**:
  - Docker: `/workspace`
  - Local: `/Users/username/projects`
  - AWS: `/home/ec2-user/workspace`

#### `VITE_DEFAULT_MODEL`
- **Type**: String (model ID)
- **Default**: `global.anthropic.claude-sonnet-4-5-20250929-v1:0`
- **Description**: Default Claude model for main responses
- **Examples**:
  - Claude Sonnet 4.5: `global.anthropic.claude-sonnet-4-5-20250929-v1:0`
  - Claude Opus 4.5: `global.anthropic.claude-opus-4-5-20250514-v1:0`
  - Via LiteLLM: `gpt-4`, `gpt-4o`, `claude-3-5-sonnet-20241022`

#### `VITE_DEFAULT_BACKGROUND_MODEL`
- **Type**: String (model ID)
- **Default**: `global.anthropic.claude-haiku-4-5-20251001-v1:0`
- **Description**: Default background model for quick tasks and agent operations
- **Examples**:
  - Claude Haiku 4.5: `global.anthropic.claude-haiku-4-5-20251001-v1:0`
  - Via LiteLLM: `gpt-4o-mini`, `claude-3-5-haiku-20241022`

#### `VITE_DEFAULT_ENABLE_PROXY`
- **Type**: Boolean (`'true'` or `'false'`)
- **Default**: `'false'`
- **Description**: Enable LiteLLM proxy by default for multi-provider support
- **Usage**: Set to `'true'` to use non-Anthropic models via LiteLLM

### UI Configuration

#### `VITE_HIDE_SETTINGS_BUTTON`
- **Type**: Boolean (`'true'` or `'false'`)
- **Default**: `'false'`
- **Description**: Hide the settings button in the header
- **Usage**: Set to `'true'` to hide the settings gear icon from the UI header
- **Use Case**: In managed deployments where you want to prevent users from changing settings

## Configuration Examples

### Example 1: Local Development (Default)

```bash
VITE_USE_INVOCATIONS=true
VITE_TERMINAL_USE_STREAMING=true
VITE_COGNITO_REGION=us-west-2
VITE_COGNITO_USER_POOL_ID=us-west-2_Sw8yyFfBT
VITE_COGNITO_CLIENT_ID=2d2cqqjvpf1ecqjg6gh1u6fivl
VITE_DEFAULT_SERVER_URL=http://127.0.0.1:8000
VITE_DEFAULT_CWD=/workspace
VITE_DEFAULT_MODEL=global.anthropic.claude-sonnet-4-5-20250929-v1:0
VITE_DEFAULT_BACKGROUND_MODEL=global.anthropic.claude-haiku-4-5-20251001-v1:0
VITE_DEFAULT_ENABLE_PROXY=false
VITE_HIDE_SETTINGS_BUTTON=false
```

### Example 2: Docker Deployment

```bash
VITE_USE_INVOCATIONS=true
VITE_TERMINAL_USE_STREAMING=true
VITE_COGNITO_REGION=us-west-2
VITE_COGNITO_USER_POOL_ID=us-west-2_Sw8yyFfBT
VITE_COGNITO_CLIENT_ID=2d2cqqjvpf1ecqjg6gh1u6fivl
VITE_DEFAULT_SERVER_URL=http://localhost:8080
VITE_DEFAULT_CWD=/workspace
VITE_DEFAULT_MODEL=global.anthropic.claude-sonnet-4-5-20250929-v1:0
VITE_DEFAULT_BACKGROUND_MODEL=global.anthropic.claude-haiku-4-5-20251001-v1:0
VITE_DEFAULT_ENABLE_PROXY=false
VITE_HIDE_SETTINGS_BUTTON=false
```

### Example 3: Production with LiteLLM Proxy

```bash
VITE_USE_INVOCATIONS=true
VITE_TERMINAL_USE_STREAMING=true
VITE_COGNITO_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID=us-east-1_ABC123XYZ
VITE_COGNITO_CLIENT_ID=abc123xyz456def789
VITE_DEFAULT_SERVER_URL=https://api.example.com
VITE_DEFAULT_CWD=/home/ubuntu/workspace
VITE_DEFAULT_MODEL=gpt-4o
VITE_DEFAULT_BACKGROUND_MODEL=gpt-4o-mini
VITE_DEFAULT_ENABLE_PROXY=true
VITE_HIDE_SETTINGS_BUTTON=false
```

### Example 4: Using AWS Bedrock Models Directly

```bash
VITE_USE_INVOCATIONS=true
VITE_TERMINAL_USE_STREAMING=true
VITE_COGNITO_REGION=us-west-2
VITE_COGNITO_USER_POOL_ID=us-west-2_Sw8yyFfBT
VITE_COGNITO_CLIENT_ID=2d2cqqjvpf1ecqjg6gh1u6fivl
VITE_DEFAULT_SERVER_URL=http://127.0.0.1:8000
VITE_DEFAULT_CWD=/workspace
VITE_DEFAULT_MODEL=us.anthropic.claude-sonnet-4-5-v1:0
VITE_DEFAULT_BACKGROUND_MODEL=us.anthropic.claude-haiku-4-5-v1:0
VITE_DEFAULT_ENABLE_PROXY=false
VITE_HIDE_SETTINGS_BUTTON=false
```

### Example 5: Managed Deployment (Settings Hidden)

For managed environments where admins control all settings:

```bash
VITE_USE_INVOCATIONS=true
VITE_TERMINAL_USE_STREAMING=true
VITE_COGNITO_REGION=us-west-2
VITE_COGNITO_USER_POOL_ID=us-west-2_Sw8yyFfBT
VITE_COGNITO_CLIENT_ID=2d2cqqjvpf1ecqjg6gh1u6fivl
VITE_DEFAULT_SERVER_URL=https://api.example.com
VITE_DEFAULT_CWD=/workspace
VITE_DEFAULT_MODEL=global.anthropic.claude-sonnet-4-5-20250929-v1:0
VITE_DEFAULT_BACKGROUND_MODEL=global.anthropic.claude-haiku-4-5-20251001-v1:0
VITE_DEFAULT_ENABLE_PROXY=false
VITE_HIDE_SETTINGS_BUTTON=true
```

## How to Use

1. **Copy the example file**:
   ```bash
   cd web_client
   cp .env.example .env
   ```

2. **Edit `.env` with your configuration**:
   - Set Cognito User Pool details
   - Adjust default server URL if needed
   - Set default models
   - Configure proxy if using non-Anthropic models

3. **Restart the development server**:
   ```bash
   npm run dev
   ```

4. **For production build**:
   ```bash
   npm run build
   ```

## Important Notes

1. **Environment variables are baked into the build**: The `VITE_*` variables are replaced at build time. After building, you cannot change them without rebuilding.

2. **User settings override defaults**: Even if you set defaults via environment variables, users can still change them in the UI Settings modal. Their choices are saved to `localStorage`.

3. **Security**: Never commit `.env` file with real credentials to version control. Use `.env.example` as a template.

4. **Vite requirement**: All client-side environment variables must be prefixed with `VITE_` to be accessible in the React app.

5. **Boolean values**: For boolean environment variables, use string `'true'` or `'false'`, not actual booleans.

## Troubleshooting

### Environment variables not taking effect

1. Restart the dev server after changing `.env`
2. For production, rebuild with `npm run build`
3. Check that variable names are prefixed with `VITE_`
4. Clear browser cache and `localStorage`

### Cognito authentication not working

1. Verify all three Cognito variables are set correctly
2. Check AWS Console for the correct Pool ID and Client ID
3. Ensure the Cognito User Pool is in the specified region
4. Verify email verification is enabled in Cognito settings

### Models not available

1. If using proxy: Ensure `VITE_DEFAULT_ENABLE_PROXY=true`
2. Check backend server has access to the specified models
3. Verify model IDs are correct for your provider
4. Check backend server logs for model-related errors

## Related Documentation

- `web_client/README.md` - Web client setup and development
- `claude/cognito-quick-setup.md` - Cognito configuration guide
- `CLAUDE.md` - Project overview and architecture
