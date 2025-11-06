# Claude Agent API Server Deployment

Complete deployment automation for the Claude Agent API Server infrastructure on AWS.

## Overview

This directory contains scripts to deploy the entire Claude Agent API Server stack:

1. **Docker Build & ECR Push** - Build and push container image to Amazon ECR
2. **AgentCore Runtime** - Deploy Bedrock AgentCore runtime with IAM roles and S3 workspace
3. **Amplify Frontend** - Deploy React web client to AWS Amplify

## Files

- `config.env.template` - Configuration template (copy to `config.env`)
- `config.env` - Your deployment configuration (not tracked in git)
- `Dockerfile` - Docker image definition
- `deploy_all.sh` - Main deployment orchestration script
- `01_build_and_push.sh` - Step 1: Build Docker image and push to ECR
- `02_deploy_agentcore.sh` - Step 2: Deploy AgentCore runtime
- `03_deploy_amplify.sh` - Step 3: Deploy Amplify frontend
- `cleanup.sh` - Delete all deployed resources
- `amplify.yml` - Amplify build configuration
- `README.md` - This documentation

## Prerequisites

### Required Tools

1. **Docker** - For building container images (must support ARM64 builds)
   ```bash
   # macOS: Install Docker Desktop (ARM64 support included)
   # Linux: Install Docker with buildx support for multi-architecture builds
   # Verify ARM64 support: docker buildx ls
   ```

2. **AWS CLI v2** - Configured with appropriate credentials
   ```bash
   aws configure
   # Ensure you have sufficient permissions for ECR, Bedrock, IAM, S3, Amplify
   ```

3. **jq** - For JSON parsing in bash scripts
   ```bash
   # macOS
   brew install jq

   # Ubuntu/Debian
   sudo apt-get install jq
   ```

4. **Node.js & npm** - For building the web client
   ```bash
   node --version  # Should be 18+
   npm --version
   ```


### AWS Permissions

Your AWS credentials need permissions for:
- **ECR**: Create repositories, push images
- **Bedrock AgentCore**: Create/update agent runtimes, workload identities
- **IAM**: Create/update roles and policies
- **S3**: Create/manage buckets
- **Amplify**: Create/update apps and deployments
- **CloudWatch Logs**: Create log groups (automatic)

## Quick Start

### 1. Create Configuration

```bash
cd deploy
cp config.env.template config.env
```

Edit `config.env` with your values:

```bash
# Minimum required configuration
AWS_REGION=us-west-2
AWS_ACCOUNT_ID=123456789012  # Optional, auto-detected if not set

# Optional: Configure Cognito for authentication
COGNITO_DISCOVERY_URL=https://cognito-idp.us-west-2.amazonaws.com/us-west-2_XXXXX/.well-known/openid-configuration
COGNITO_CLIENT_ID=your-client-id

# Optional: Change default values
AGENT_RUNTIME_NAME=claude_code
ECR_REPOSITORY_NAME=agentcore/claude-code
```

### 2. Deploy Everything

```bash
./deploy_all.sh
```

This will:
1. ✅ Build and push Docker image to ECR
2. ✅ Create S3 workspace bucket
3. ✅ Create Cognito User Pool and App Client (for authentication)
4. ✅ Create IAM execution role with required permissions
5. ✅ Deploy AgentCore runtime with your container
6. ✅ Build and deploy frontend to Amplify
7. ✅ Configure environment variables automatically

### 3. Access Your Application

After deployment completes, you'll see:
```
Deployment Complete!
-------------------------------------------
Amplify Frontend:
  URL: https://main.xxxxx.amplifyapp.com
  App ID: xxxxxxxxxxxxx
```

## Individual Deployment Steps

You can also run steps individually:

### Step 1: Build and Push Docker Image

```bash
./01_build_and_push.sh
```

Creates/updates ECR repository and pushes Docker image.

**What it does:**
- Creates ECR repository if it doesn't exist
- Builds Docker image from `deploy/Dockerfile` **for ARM64 architecture**
- Pushes image to ECR with configured tag
- Saves image URI for next step

**Important:** Images are built for ARM64 architecture as required by Bedrock AgentCore.

**Idempotent:** Can be run multiple times safely

### Step 2: Deploy AgentCore Runtime

```bash
./02_deploy_agentcore.sh
```

Creates/updates all AgentCore infrastructure.

**What it does:**
- Creates S3 workspace bucket
- **Creates Cognito User Pool and App Client** (if not provided in config)
  - Configures password policy
  - Sets up JWT authentication
  - Configures OIDC discovery URL
- Creates IAM execution role with trust policy and permissions:
  - ECR image access
  - CloudWatch Logs
  - Bedrock model invocation
  - S3 workspace access
  - AgentCore workload identity access
- Creates or updates AgentCore runtime:
  - Container configuration
  - Network mode (PUBLIC)
  - Environment variables
  - JWT authorizer with Cognito
  - OAuth callback URLs
- Saves runtime ARN and Cognito configuration for next step

**Idempotent:** Updates existing resources if found

### Step 3: Deploy Amplify Frontend

```bash
./03_deploy_amplify.sh
```

Deploys the React web client to AWS Amplify.

**What it does:**
- Creates Amplify app if it doesn't exist
- Configures SPA redirect rules
- Loads environment variables from `web_client/.env`
- Builds web client with `npm run build`
- Creates deployment package
- Uploads and deploys to Amplify
- Provides access URL

**Idempotent:** Updates existing app if found

## Configuration Reference

### Core Settings

```bash
# AWS Configuration
AWS_REGION=us-west-2              # AWS region for all resources
AWS_ACCOUNT_ID=                   # Auto-detected if not set

# Project Configuration
PROJECT_NAME=claude-agent-api-server
DEPLOYMENT_ENV=prod               # Environment tag
```

### Docker/ECR Settings

```bash
ECR_REPOSITORY_NAME=agentcore/claude-code  # ECR repository name
DOCKER_IMAGE_VERSION=latest                # Image tag
```

### AgentCore Settings

```bash
AGENT_RUNTIME_NAME=claude_code                    # Runtime name
IAM_ROLE_NAME=AmazonBedrockAgentCoreSDKRuntime   # IAM role prefix
S3_WORKSPACE_BUCKET_PREFIX=agentcore              # S3 bucket prefix
# Note: Actual bucket name will be: agentcore-{region}-{account_id}
```

### Authentication (Optional)

```bash
# Cognito JWT authorizer configuration
COGNITO_DISCOVERY_URL=https://cognito-idp.REGION.amazonaws.com/POOL_ID/.well-known/openid-configuration
COGNITO_CLIENT_ID=your-client-id
```

### Bedrock Models

```bash
ANTHROPIC_MODEL=global.anthropic.claude-sonnet-4-5-20250929-v1:0
ANTHROPIC_SMALL_FAST_MODEL=global.anthropic.claude-haiku-4-5-20251001-v1:0
ANTHROPIC_DEFAULT_HAIKU_MODEL=global.anthropic.claude-haiku-4-5-20251001-v1:0
DISABLE_PROMPT_CACHING=0
CLAUDE_CODE_USE_BEDROCK=1
```

### Amplify Settings

```bash
AMPLIFY_APP_NAME=claude-agent-web-client
AMPLIFY_BRANCH_NAME=main
GITHUB_REPO=https://github.com/yytdfc/claude-agent-api-server.git
```

## Resource Naming

All resources are created with consistent naming:

| Resource | Name Pattern | Example |
|----------|-------------|---------|
| ECR Repository | `${ECR_REPOSITORY_NAME}` | `agentcore/claude-code` |
| AgentCore Runtime | `${AGENT_RUNTIME_NAME}` | `claude_code` |
| IAM Role | `${IAM_ROLE_NAME}-${REGION}-${ENV}` | `AmazonBedrockAgentCoreSDKRuntime-us-west-2-prod` |
| S3 Bucket | `${S3_WORKSPACE_BUCKET_PREFIX}-${REGION}-${ACCOUNT_ID}` | `agentcore-us-west-2-123456789012` |
| Amplify App | `${AMPLIFY_APP_NAME}` | `claude-agent-web-client` |
| CloudWatch Logs | `/aws/bedrock-agentcore/runtimes/${AGENT_RUNTIME_NAME}` | `/aws/bedrock-agentcore/runtimes/claude_code` |

## Updating Deployments

### Update Application Code

```bash
# Make code changes, then:
./deploy_all.sh
```

This will rebuild and redeploy everything.

### Update Configuration Only

```bash
# Edit config.env
vi config.env

# Redeploy (will use new configuration)
./deploy_all.sh
```

### Update Frontend Only

```bash
# Edit web_client code
# Edit web_client/.env for environment variables

# Deploy just frontend
./03_deploy_amplify.sh
```

## Monitoring

### View AgentCore Logs

```bash
# Tail logs in real-time
aws logs tail /aws/bedrock-agentcore/runtimes/claude_code --follow --region us-west-2

# Get recent logs
aws logs tail /aws/bedrock-agentcore/runtimes/claude_code --since 1h --region us-west-2
```

### Check AgentCore Status

```bash
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id <runtime-id> \
  --region us-west-2
```

### Check Amplify Deployment

```bash
# List deployments
aws amplify list-jobs \
  --app-id <app-id> \
  --branch-name main \
  --region us-west-2

# Get deployment details
aws amplify get-job \
  --app-id <app-id> \
  --branch-name main \
  --job-id <job-id> \
  --region us-west-2
```

### AWS Console Links

- **Bedrock AgentCore**: https://console.aws.amazon.com/bedrock/home?region=us-west-2#/agentcore
- **Amplify**: https://console.aws.amazon.com/amplify/home?region=us-west-2
- **ECR**: https://console.aws.amazon.com/ecr/repositories?region=us-west-2
- **CloudWatch Logs**: https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#logsV2:log-groups

## Cleanup

### Delete All Resources

```bash
./cleanup.sh
```

This will prompt for confirmation, then delete:
1. ✅ Amplify app and all deployments
2. ✅ AgentCore runtime
3. ✅ IAM role and policies
4. ✅ S3 workspace bucket (after emptying)
5. ✅ ECR repository (optional, will prompt)

**Note:** CloudWatch Logs are not automatically deleted to preserve audit history. Delete manually if needed:

```bash
aws logs delete-log-group \
  --log-group-name /aws/bedrock-agentcore/runtimes/claude_code \
  --region us-west-2
```

## Troubleshooting

### Docker build fails

**Check:**
- Docker daemon is running
- Dockerfile exists at `deploy/Dockerfile`
- Build context is correct (project root directory)

### Docker ARM64 build not supported

**Error:** `failed to solve: failed to load build definition`

**Solution:**
```bash
# On Linux, enable buildx for multi-architecture support
docker buildx create --name multiarch --driver docker-container --use
docker buildx inspect --bootstrap

# Verify ARM64 support
docker buildx ls
```

On macOS with Apple Silicon, ARM64 support is native. On Intel Macs or Linux x86_64, Docker will use QEMU emulation for ARM64 builds.

### ECR push fails with authentication error

```bash
# Re-authenticate to ECR
aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.us-west-2.amazonaws.com
```

### IAM role creation fails

**Check:**
- Your AWS credentials have `iam:CreateRole` permission
- Role name doesn't conflict with existing role
- Trust policy is valid

### AgentCore runtime creation fails

**Common causes:**
- IAM role not ready (script waits 10s, may need more time)
- Invalid container URI format
- Region not supported for Bedrock AgentCore
- Cognito configuration invalid

**Solution:**
```bash
# Wait a minute for IAM propagation, then retry
./02_deploy_agentcore.sh
```

### Amplify build fails

**Check:**
- `web_client/.env` file exists and is valid
- Node modules installed: `cd web_client && npm install`
- Build works locally: `cd web_client && npm run build`

### Environment variables not updating

Environment variables are set from:
1. `config.env` - Main configuration
2. `web_client/.env` - Frontend-specific variables
3. Previous step outputs (`.build_output`, `.agentcore_output`)

To force update:
```bash
# Edit configuration
vi config.env
vi web_client/.env

# Redeploy
./deploy_all.sh
```

### S3 bucket already exists

S3 bucket names are global. The default naming pattern includes region and account ID for uniqueness:
- Pattern: `{prefix}-{region}-{account_id}`
- Example: `agentcore-us-west-2-123456789012`

If bucket name conflicts still occur:
1. Edit `config.env`
2. Change `S3_WORKSPACE_BUCKET_PREFIX` to a different prefix
3. Redeploy

### Cannot delete S3 bucket

Bucket must be empty before deletion:
```bash
# Replace with your actual bucket name
aws s3 rm s3://agentcore-us-west-2-123456789012 --recursive --region us-west-2
aws s3api delete-bucket --bucket agentcore-us-west-2-123456789012 --region us-west-2
```

## Security Best Practices

1. **Secrets Management**: Never commit `config.env` to git
2. **IAM Roles**: Use least-privilege permissions
3. **S3 Buckets**: Enable encryption at rest (default)
4. **Network**: Use VPC mode for private resources (currently PUBLIC)
5. **Cognito**: Enable MFA for production deployments
6. **Logs**: Enable CloudWatch Logs encryption

## Cost Estimates

Approximate monthly costs (us-west-2, subject to change):

| Service | Usage | Estimated Cost |
|---------|-------|----------------|
| Bedrock AgentCore Runtime | 24/7 running | ~$50-100/month |
| Bedrock Model Invocations | Pay per use | Variable |
| S3 Workspace | ~10GB storage | ~$0.23/month |
| Amplify Hosting | Basic hosting | ~$0.15/GB served |
| ECR Storage | ~1GB images | ~$0.10/month |
| CloudWatch Logs | ~1GB logs/month | ~$0.50/month |

**Total**: ~$51-102/month + model invocation costs

## Advanced Configuration

### Using VPC Mode

Edit `02_deploy_agentcore.py`:

```python
'networkConfiguration': {
    'networkMode': 'VPC',
    'networkModeConfig': {
        'securityGroups': ['sg-xxxxx'],
        'subnets': ['subnet-xxxxx', 'subnet-yyyyy']
    }
}
```

### Custom OAuth Callback URLs

For multiple environments:

```bash
# In config.env
OAUTH_CALLBACK_URL=https://app.example.com/oauth/callback,http://localhost:8080/oauth/callback
```

Update script to handle multiple URLs.

### GitHub CI/CD Integration

After first deployment:
1. Open Amplify Console
2. Connect GitHub repository
3. Select branch
4. Configure build settings (uses `amplify.yml`)
5. Enable automatic deployments

## Support

For issues and questions:
- Check troubleshooting section above
- Review CloudWatch Logs
- Check AWS service quotas
- Verify AWS credentials and permissions

## References

- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/)
- [AWS Amplify Documentation](https://docs.aws.amazon.com/amplify/)
- [Amazon ECR Documentation](https://docs.aws.amazon.com/ecr/)
- [IAM Roles Documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html)
