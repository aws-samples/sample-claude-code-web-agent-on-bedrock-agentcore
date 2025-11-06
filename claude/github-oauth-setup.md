# GitHub OAuth Identity Provider Setup

## Overview

The deployment now requires GitHub OAuth configuration for AgentCore Identity Provider. This enables GitHub integration features like repository access, code synchronization, and gh CLI authentication.

## Why This is Required

- AgentCore Identity Provider needs OAuth credentials to authenticate users with GitHub
- Without this configuration, GitHub-related features will not work
- The deployment script will fail with a detailed error message if credentials are missing

## Setup Steps

### 1. Create GitHub OAuth App

1. Go to GitHub Settings → Developer settings → OAuth Apps
   - Direct URL: https://github.com/settings/developers

2. Click **"New OAuth App"**

3. Fill in the application details:
   - **Application name**: Claude Agent (or any name you prefer)
   - **Homepage URL**: Your application URL (can be placeholder)
   - **Authorization callback URL**:
     ```
     https://bedrock-agentcore.<REGION>.amazonaws.com/identities/oauth2/callback
     ```
     Replace `<REGION>` with your AWS region (e.g., `us-west-2`)

4. Click **"Register application"**

### 2. Obtain Credentials

1. After creating the app, you'll see the **Client ID** - copy it

2. Click **"Generate a new client secret"**

3. **Important**: Copy the client secret immediately
   - GitHub only shows the full secret once when it's generated
   - If you lose it, you'll need to generate a new one

### 3. Configure Deployment

Add the credentials to `deploy/config.env`:

```bash
# GitHub OAuth Configuration
GITHUB_OAUTH_CLIENT_ID=your-github-client-id
GITHUB_OAUTH_CLIENT_SECRET=your-github-client-secret
```

### 4. Deploy

Run the deployment script:

```bash
cd deploy
./02_deploy_agentcore.sh
```

The script will:
- Validate that GitHub OAuth credentials are present
- Create or update the GitHub OAuth2 credential provider in AgentCore
- Continue with the rest of the deployment

## Error Handling

If you run the deployment without configuring GitHub OAuth, you'll see:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ERROR: GitHub OAuth configuration is missing!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

The script will display detailed setup instructions and exit.

## How It Works

### Deployment Script Behavior

1. **Check for credentials**: Script checks if `GITHUB_OAUTH_CLIENT_ID` and `GITHUB_OAUTH_CLIENT_SECRET` are set

2. **Create provider**: If credentials exist, script calls:
   ```bash
   aws bedrock-agentcore-control create-oauth2-credential-provider \
       --name "github-provider-prod" \
       --credential-provider-vendor "GithubOauth2" \
       --oauth2-provider-config-input "githubOauth2ProviderConfig={clientId=...,clientSecret=...}" \
       --region us-west-2
   ```

3. **Update if exists**: If the provider already exists, the script updates it with new credentials

### Runtime Behavior

When the AgentCore runtime receives a request for GitHub authentication:

1. User requests GitHub access (e.g., via `/oauth/github/token` endpoint)
2. AgentCore Identity looks up the configured GitHub OAuth provider
3. Initiates OAuth flow using the configured Client ID and Secret
4. Returns authorization URL to user (if first time) or access token (if authorized)
5. User authorizes the app on GitHub
6. GitHub redirects to AgentCore callback URL
7. AgentCore exchanges authorization code for access token
8. Access token is stored in AgentCore Token Vault
9. Token is returned to the application

## AWS CLI Commands

### List OAuth Providers

```bash
aws bedrock-agentcore-control list-oauth2-credential-providers \
    --region us-west-2
```

### Get Provider Details

```bash
aws bedrock-agentcore-control get-oauth2-credential-provider \
    --oauth2-credential-provider-id <provider-id> \
    --region us-west-2
```

### Update Provider

```bash
aws bedrock-agentcore-control update-oauth2-credential-provider \
    --oauth2-credential-provider-id <provider-id> \
    --region us-west-2 \
    --oauth2-provider-config-input "githubOauth2ProviderConfig={clientId=NEW_ID,clientSecret=NEW_SECRET}"
```

### Delete Provider

```bash
aws bedrock-agentcore-control delete-oauth2-credential-provider \
    --oauth2-credential-provider-id <provider-id> \
    --region us-west-2
```

## Security Notes

1. **Client Secret Protection**:
   - Never commit `config.env` to git (it's in .gitignore)
   - Store secrets securely (consider using AWS Secrets Manager for production)

2. **Callback URL**:
   - Must exactly match what's configured in GitHub OAuth App
   - Must use HTTPS (AWS provides secure endpoint)

3. **Credential Rotation**:
   - Regenerate secrets periodically
   - Update both GitHub OAuth App and deployment config
   - Re-run deployment to update AgentCore provider

## Troubleshooting

### "Could not create GitHub provider"

- Check AWS credentials have proper permissions
- Verify region is correct
- Ensure Client ID and Secret are correct

### "Authorization failed"

- Verify callback URL matches exactly (including region)
- Check GitHub OAuth App is not suspended
- Ensure user has access to the GitHub organization/repositories

### "Token expired"

- AgentCore automatically refreshes tokens when possible
- If refresh fails, user needs to re-authorize

## References

- [AWS Bedrock AgentCore Identity - GitHub Provider](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-idp-github.html)
- [AWS CLI - create-oauth2-credential-provider](https://docs.aws.amazon.com/cli/latest/reference/bedrock-agentcore-control/create-oauth2-credential-provider.html)
- [GitHub OAuth Apps Documentation](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app)
