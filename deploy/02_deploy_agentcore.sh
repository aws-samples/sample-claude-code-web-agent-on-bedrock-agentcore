#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.env"

if [ -f "${SCRIPT_DIR}/.build_output" ]; then
    source "${SCRIPT_DIR}/.build_output"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Step 2: Deploy AgentCore Runtime${NC}"
echo "======================================"

if [ -z "$AWS_REGION" ]; then
    AWS_REGION=$(aws configure get region)
    AWS_REGION=${AWS_REGION:-us-west-2}
fi

if [ -z "$AWS_ACCOUNT_ID" ]; then
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    echo -e "${GREEN}Detected AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}${NC}"
fi

if [ -z "$DOCKER_IMAGE_URI" ]; then
    echo -e "${RED}Error: Docker image URI not found. Please run step 1 first.${NC}"
    exit 1
fi

echo ""
echo "Configuration:"
echo "  Region: ${AWS_REGION}"
echo "  Account ID: ${AWS_ACCOUNT_ID}"
echo "  Docker Image: ${DOCKER_IMAGE_URI}"
echo ""

# Create S3 workspace bucket
echo -e "${YELLOW}Checking S3 workspace bucket...${NC}"
BUCKET_PREFIX="${S3_WORKSPACE_BUCKET_PREFIX:-agentcore}"
BUCKET_NAME="${BUCKET_PREFIX}-${AWS_REGION}-${AWS_ACCOUNT_ID}"

if aws s3 ls "s3://${BUCKET_NAME}" &>/dev/null; then
    echo -e "${GREEN}✓${NC} S3 bucket already exists: ${BUCKET_NAME}"
else
    echo -e "${YELLOW}Creating S3 bucket: ${BUCKET_NAME}${NC}"

    if [ "$AWS_REGION" == "us-east-1" ]; then
        aws s3api create-bucket --bucket "${BUCKET_NAME}" --region "${AWS_REGION}"
    else
        aws s3api create-bucket \
            --bucket "${BUCKET_NAME}" \
            --region "${AWS_REGION}" \
            --create-bucket-configuration LocationConstraint="${AWS_REGION}"
    fi

    echo -e "${GREEN}✓${NC} S3 bucket created"
fi

# Setup Cognito
echo ""
echo -e "${YELLOW}Checking Cognito User Pool...${NC}"

COGNITO_POOL_NAME="${COGNITO_USER_POOL_NAME:-ClaudeAgentPool-${DEPLOYMENT_ENV:-prod}}"
COGNITO_CLIENT_NAME="${COGNITO_CLIENT_NAME:-ClaudeAgentClient-${DEPLOYMENT_ENV:-prod}}"

if [ -z "$COGNITO_USER_POOL_ID" ] || [ -z "$COGNITO_CLIENT_ID" ]; then
    echo -e "${YELLOW}No Cognito configuration found. Creating new Cognito setup...${NC}"

    # Check if pool already exists
    EXISTING_POOL=$(aws cognito-idp list-user-pools --max-results 60 --region "${AWS_REGION}" \
        --query "UserPools[?Name=='${COGNITO_POOL_NAME}'].Id" --output text)

    if [ -n "$EXISTING_POOL" ]; then
        COGNITO_USER_POOL_ID="$EXISTING_POOL"
        echo -e "${GREEN}✓${NC} Cognito User Pool already exists: ${COGNITO_USER_POOL_ID}"
    else
        echo -e "${YELLOW}Creating Cognito User Pool: ${COGNITO_POOL_NAME}${NC}"

        CREATE_POOL_OUTPUT=$(aws cognito-idp create-user-pool \
            --pool-name "${COGNITO_POOL_NAME}" \
            --region "${AWS_REGION}" \
            --policies '{
                "PasswordPolicy": {
                    "MinimumLength": 8,
                    "RequireUppercase": false,
                    "RequireLowercase": false,
                    "RequireNumbers": false,
                    "RequireSymbols": false,
                    "TemporaryPasswordValidityDays": 7
                }
            }' \
            --auto-verified-attributes email \
            --mfa-configuration OFF \
            --email-configuration EmailSendingAccount=COGNITO_DEFAULT \
            --admin-create-user-config AllowAdminCreateUserOnly=false \
            --account-recovery-setting '{
                "RecoveryMechanisms": [
                    {"Priority": 1, "Name": "verified_email"},
                    {"Priority": 2, "Name": "verified_phone_number"}
                ]
            }' \
            --user-pool-tags \
                Project="${TAG_PROJECT:-claude-agent}" \
            --output json)

        COGNITO_USER_POOL_ID=$(echo "$CREATE_POOL_OUTPUT" | jq -r '.UserPool.Id')
        echo -e "${GREEN}✓${NC} Cognito User Pool created: ${COGNITO_USER_POOL_ID}"
    fi

    COGNITO_DISCOVERY_URL="https://cognito-idp.${AWS_REGION}.amazonaws.com/${COGNITO_USER_POOL_ID}/.well-known/openid-configuration"

    # Check if client already exists
    EXISTING_CLIENT=$(aws cognito-idp list-user-pool-clients \
        --user-pool-id "${COGNITO_USER_POOL_ID}" \
        --max-results 60 \
        --region "${AWS_REGION}" \
        --query "UserPoolClients[?ClientName=='${COGNITO_CLIENT_NAME}'].ClientId" \
        --output text)

    if [ -n "$EXISTING_CLIENT" ]; then
        COGNITO_CLIENT_ID="$EXISTING_CLIENT"
        echo -e "${GREEN}✓${NC} Cognito App Client already exists: ${COGNITO_CLIENT_ID}"
    else
        echo -e "${YELLOW}Creating Cognito App Client: ${COGNITO_CLIENT_NAME}${NC}"

        CREATE_CLIENT_OUTPUT=$(aws cognito-idp create-user-pool-client \
            --user-pool-id "${COGNITO_USER_POOL_ID}" \
            --client-name "${COGNITO_CLIENT_NAME}" \
            --region "${AWS_REGION}" \
            --refresh-token-validity 30 \
            --access-token-validity 1 \
            --id-token-validity 1 \
            --token-validity-units AccessToken=days,IdToken=days,RefreshToken=days \
            --explicit-auth-flows ALLOW_REFRESH_TOKEN_AUTH ALLOW_USER_PASSWORD_AUTH ALLOW_USER_SRP_AUTH \
            --enable-token-revocation \
            --prevent-user-existence-errors ENABLED \
            --output json)

        COGNITO_CLIENT_ID=$(echo "$CREATE_CLIENT_OUTPUT" | jq -r '.UserPoolClient.ClientId')
        echo -e "${GREEN}✓${NC} Cognito App Client created: ${COGNITO_CLIENT_ID}"
    fi

    echo ""
    echo -e "${GREEN}Cognito Configuration:${NC}"
    echo "  User Pool ID: ${COGNITO_USER_POOL_ID}"
    echo "  Client ID: ${COGNITO_CLIENT_ID}"
    echo "  Discovery URL: ${COGNITO_DISCOVERY_URL}"
    echo "  Region: ${AWS_REGION}"
else
    echo -e "${GREEN}✓${NC} Using existing Cognito configuration from config.env"
    echo "  User Pool ID: ${COGNITO_USER_POOL_ID}"
    echo "  Client ID: ${COGNITO_CLIENT_ID}"
    COGNITO_DISCOVERY_URL="https://cognito-idp.${AWS_REGION}.amazonaws.com/${COGNITO_USER_POOL_ID}/.well-known/openid-configuration"
fi

# Create IAM role
echo ""
echo -e "${YELLOW}Checking IAM execution role...${NC}"

FULL_ROLE_NAME="${IAM_ROLE_NAME}-${AWS_REGION}-${DEPLOYMENT_ENV:-prod}"

if aws iam get-role --role-name "${FULL_ROLE_NAME}" &>/dev/null; then
    ROLE_ARN=$(aws iam get-role --role-name "${FULL_ROLE_NAME}" --query 'Role.Arn' --output text)
    echo -e "${GREEN}✓${NC} IAM role already exists: ${ROLE_ARN}"
else
    echo -e "${YELLOW}Creating IAM role: ${FULL_ROLE_NAME}${NC}"

    # Create trust policy
    cat > /tmp/trust-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Sid": "AssumeRolePolicy",
        "Effect": "Allow",
        "Principal": {
            "Service": "bedrock-agentcore.amazonaws.com"
        },
        "Action": "sts:AssumeRole",
        "Condition": {
            "StringEquals": {
                "aws:SourceAccount": "${AWS_ACCOUNT_ID}"
            },
            "ArnLike": {
                "aws:SourceArn": "arn:aws:bedrock-agentcore:${AWS_REGION}:${AWS_ACCOUNT_ID}:*"
            }
        }
    }]
}
EOF

    ROLE_ARN=$(aws iam create-role \
        --role-name "${FULL_ROLE_NAME}" \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --description "Execution role for Bedrock AgentCore Runtime" \
        --tags \
            Key=Project,Value="${TAG_PROJECT:-claude-agent}" \
            Key=Environment,Value="${TAG_ENVIRONMENT:-production}" \
            Key=ManagedBy,Value="${TAG_MANAGED_BY:-deployment-script}" \
        --query 'Role.Arn' \
        --output text)

    echo -e "${GREEN}✓${NC} IAM role created: ${ROLE_ARN}"
    rm /tmp/trust-policy.json
fi

# Update role policy
echo -e "${YELLOW}Updating IAM role policy...${NC}"

cat > /tmp/role-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ECRImageAccess",
            "Effect": "Allow",
            "Action": [
                "ecr:BatchGetImage",
                "ecr:GetDownloadUrlForLayer"
            ],
            "Resource": ["arn:aws:ecr:${AWS_REGION}:${AWS_ACCOUNT_ID}:repository/*"]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:DescribeLogStreams",
                "logs:CreateLogGroup"
            ],
            "Resource": ["arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:/aws/bedrock-agentcore/runtimes/*"]
        },
        {
            "Effect": "Allow",
            "Action": ["logs:DescribeLogGroups"],
            "Resource": ["arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:*"]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": ["arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"]
        },
        {
            "Sid": "ECRTokenAccess",
            "Effect": "Allow",
            "Action": ["ecr:GetAuthorizationToken"],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "xray:PutTraceSegments",
                "xray:PutTelemetryRecords",
                "xray:GetSamplingRules",
                "xray:GetSamplingTargets"
            ],
            "Resource": ["*"]
        },
        {
            "Effect": "Allow",
            "Resource": "*",
            "Action": "cloudwatch:PutMetricData",
            "Condition": {
                "StringEquals": {
                    "cloudwatch:namespace": "bedrock-agentcore"
                }
            }
        },
        {
            "Sid": "GetAgentAccessToken",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:GetWorkloadAccessToken",
                "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                "bedrock-agentcore:GetWorkloadAccessTokenForUserId"
            ],
            "Resource": [
                "arn:aws:bedrock-agentcore:${AWS_REGION}:${AWS_ACCOUNT_ID}:workload-identity-directory/default",
                "arn:aws:bedrock-agentcore:${AWS_REGION}:${AWS_ACCOUNT_ID}:workload-identity-directory/default/workload-identity/*"
            ]
        },
        {
            "Sid": "BedrockModelInvocation",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/*",
                "arn:aws:bedrock:${AWS_REGION}:${AWS_ACCOUNT_ID}:*"
            ]
        },
        {
            "Sid": "S3WorkspaceAccess",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::${BUCKET_NAME}",
                "arn:aws:s3:::${BUCKET_NAME}/*"
            ]
        }
    ]
}
EOF

aws iam put-role-policy \
    --role-name "${FULL_ROLE_NAME}" \
    --policy-name "AgentCoreRuntimePolicy" \
    --policy-document file:///tmp/role-policy.json

echo -e "${GREEN}✓${NC} IAM role policy updated"
rm /tmp/role-policy.json

echo -e "${YELLOW}Waiting 10 seconds for IAM role to propagate...${NC}"
sleep 10

# Create or update AgentCore Runtime
echo ""
echo -e "${YELLOW}Checking AgentCore Runtime...${NC}"

RUNTIME_NAME="${AGENT_RUNTIME_NAME}"

EXISTING_RUNTIME=$(aws bedrock-agentcore-control list-agent-runtimes --region "${AWS_REGION}" \
    --query "agentRuntimes[?agentRuntimeName=='${RUNTIME_NAME}'].agentRuntimeId" --output text 2>/dev/null || echo "")

# Prepare environment variables
ENV_VARS="AWS_DEFAULT_REGION=${AWS_REGION}"
[ -n "${ANTHROPIC_MODEL}" ] && ENV_VARS="${ENV_VARS},ANTHROPIC_MODEL=${ANTHROPIC_MODEL}"
[ -n "${ANTHROPIC_SMALL_FAST_MODEL}" ] && ENV_VARS="${ENV_VARS},ANTHROPIC_SMALL_FAST_MODEL=${ANTHROPIC_SMALL_FAST_MODEL}"
[ -n "${ANTHROPIC_DEFAULT_HAIKU_MODEL}" ] && ENV_VARS="${ENV_VARS},ANTHROPIC_DEFAULT_HAIKU_MODEL=${ANTHROPIC_DEFAULT_HAIKU_MODEL}"
[ -n "${DISABLE_PROMPT_CACHING}" ] && ENV_VARS="${ENV_VARS},DISABLE_PROMPT_CACHING=${DISABLE_PROMPT_CACHING}"
[ -n "${CLAUDE_CODE_USE_BEDROCK}" ] && ENV_VARS="${ENV_VARS},CLAUDE_CODE_USE_BEDROCK=${CLAUDE_CODE_USE_BEDROCK}"
ENV_VARS="${ENV_VARS},S3_WORKSPACE_BUCKET=${BUCKET_NAME}"
[ -n "${OAUTH_CALLBACK_URL}" ] && ENV_VARS="${ENV_VARS},OAUTH_CALLBACK_URL=${OAUTH_CALLBACK_URL}"

# Prepare authorizer configuration
if [ -n "$COGNITO_DISCOVERY_URL" ] && [ -n "$COGNITO_CLIENT_ID" ]; then
    AUTHORIZER_CONFIG="customJWTAuthorizer={discoveryUrl=${COGNITO_DISCOVERY_URL},allowedClients=[${COGNITO_CLIENT_ID}]}"
else
    AUTHORIZER_CONFIG=""
fi

if [ -n "$EXISTING_RUNTIME" ]; then
    echo -e "${YELLOW}Updating existing AgentCore Runtime: ${EXISTING_RUNTIME}${NC}"

    if [ -n "$AUTHORIZER_CONFIG" ]; then
        aws bedrock-agentcore-control update-agent-runtime \
            --agent-runtime-id "${EXISTING_RUNTIME}" \
            --region "${AWS_REGION}" \
            --agent-runtime-artifact "containerConfiguration={containerUri=${DOCKER_IMAGE_URI}}" \
            --network-configuration "networkMode=PUBLIC" \
            --role-arn "${ROLE_ARN}" \
            --request-header-configuration "requestHeaderAllowlist=[Authorization]" \
            --environment-variables "${ENV_VARS}" \
            --authorizer-configuration "${AUTHORIZER_CONFIG}" \
            --output json > /tmp/runtime-output.json
    else
        aws bedrock-agentcore-control update-agent-runtime \
            --agent-runtime-id "${EXISTING_RUNTIME}" \
            --region "${AWS_REGION}" \
            --agent-runtime-artifact "containerConfiguration={containerUri=${DOCKER_IMAGE_URI}}" \
            --network-configuration "networkMode=PUBLIC" \
            --role-arn "${ROLE_ARN}" \
            --request-header-configuration "requestHeaderAllowlist=[Authorization]" \
            --environment-variables "${ENV_VARS}" \
            --output json > /tmp/runtime-output.json
    fi

    RUNTIME_ID="${EXISTING_RUNTIME}"
    echo -e "${GREEN}✓${NC} AgentCore Runtime updated"
else
    echo -e "${YELLOW}Creating new AgentCore Runtime: ${RUNTIME_NAME}${NC}"

    if [ -n "$AUTHORIZER_CONFIG" ]; then
        aws bedrock-agentcore-control create-agent-runtime \
            --agent-runtime-name "${RUNTIME_NAME}" \
            --region "${AWS_REGION}" \
            --agent-runtime-artifact "containerConfiguration={containerUri=${DOCKER_IMAGE_URI}}" \
            --network-configuration "networkMode=PUBLIC" \
            --role-arn "${ROLE_ARN}" \
            --request-header-configuration "requestHeaderAllowlist=[Authorization]" \
            --environment-variables "${ENV_VARS}" \
            --authorizer-configuration "${AUTHORIZER_CONFIG}" \
            --output json > /tmp/runtime-output.json
    else
        aws bedrock-agentcore-control create-agent-runtime \
            --agent-runtime-name "${RUNTIME_NAME}" \
            --region "${AWS_REGION}" \
            --agent-runtime-artifact "containerConfiguration={containerUri=${DOCKER_IMAGE_URI}}" \
            --network-configuration "networkMode=PUBLIC" \
            --role-arn "${ROLE_ARN}" \
            --request-header-configuration "requestHeaderAllowlist=[Authorization]" \
            --environment-variables "${ENV_VARS}" \
            --output json > /tmp/runtime-output.json
    fi

    RUNTIME_ID=$(jq -r '.agentRuntimeId' /tmp/runtime-output.json)
    echo -e "${GREEN}✓${NC} AgentCore Runtime created: ${RUNTIME_ID}"
fi

RUNTIME_ARN=$(jq -r '.agentRuntimeArn' /tmp/runtime-output.json)
WORKLOAD_IDENTITY_ARN=$(jq -r '.workloadIdentityDetails.workloadIdentityArn' /tmp/runtime-output.json)
STATUS=$(jq -r '.status' /tmp/runtime-output.json)

# Construct Runtime URL for web client
# URL encode the ARN for use in URL path
ENCODED_ARN=$(echo "${RUNTIME_ARN}" | sed 's/:/%3A/g' | sed 's/\//%2F/g')
RUNTIME_URL="https://bedrock-agentcore.${AWS_REGION}.amazonaws.com/runtimes/${ENCODED_ARN}"

echo ""
echo -e "${GREEN}AgentCore Runtime Details:${NC}"
echo "  Runtime ID: ${RUNTIME_ID}"
echo "  Runtime ARN: ${RUNTIME_ARN}"
echo "  Runtime URL: ${RUNTIME_URL}"
echo "  Status: ${STATUS}"
echo "  Workload Identity ARN: ${WORKLOAD_IDENTITY_ARN}"

rm /tmp/runtime-output.json

# Update workload identity OAuth callback URLs
if [ -n "$OAUTH_CALLBACK_URL" ]; then
    echo ""
    echo -e "${YELLOW}Updating workload identity OAuth callback URLs...${NC}"
    WORKLOAD_IDENTITY_NAME=$(echo "$WORKLOAD_IDENTITY_ARN" | awk -F'/' '{print $NF}')

    aws bedrock-agentcore-control update-workload-identity \
        --name "${WORKLOAD_IDENTITY_NAME}" \
        --region "${AWS_REGION}" \
        --allowed-resource-oauth2-return-urls "${OAUTH_CALLBACK_URL}" \
        2>/dev/null || echo -e "${YELLOW}Warning: Could not update workload identity OAuth URLs${NC}"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Workload identity OAuth URLs updated"
    fi
fi

# Save outputs
cat > "${SCRIPT_DIR}/.agentcore_output" <<EOF
export AGENT_RUNTIME_ARN=${RUNTIME_ARN}
export AGENT_RUNTIME_URL=${RUNTIME_URL}
export WORKLOAD_IDENTITY_ARN=${WORKLOAD_IDENTITY_ARN}
export IAM_ROLE_ARN=${ROLE_ARN}
export S3_WORKSPACE_BUCKET=${BUCKET_NAME}
export COGNITO_USER_POOL_ID=${COGNITO_USER_POOL_ID}
export COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
export COGNITO_DISCOVERY_URL=${COGNITO_DISCOVERY_URL}
export COGNITO_REGION=${AWS_REGION}
EOF

# Configure GitHub Identity Provider
echo ""
echo -e "${YELLOW}Checking GitHub Identity Provider configuration...${NC}"

if [ -z "$GITHUB_OAUTH_CLIENT_ID" ] || [ -z "$GITHUB_OAUTH_CLIENT_SECRET" ]; then
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}ERROR: GitHub OAuth configuration is missing!${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}GitHub integration features require an OAuth App to be configured.${NC}"
    echo ""
    echo -e "${YELLOW}Please follow these steps:${NC}"
    echo ""
    echo "1. Go to GitHub Settings → Developer settings → OAuth Apps"
    echo "   URL: https://github.com/settings/developers"
    echo ""
    echo "2. Click 'New OAuth App' and fill in:"
    echo "   - Application name: Claude Agent (or any name you prefer)"
    echo "   - Homepage URL: Your application URL"
    echo "   - Authorization callback URL:"
    echo -e "     ${GREEN}https://bedrock-agentcore.${AWS_REGION}.amazonaws.com/identities/oauth2/callback${NC}"
    echo ""
    echo "3. After creating the app, copy the Client ID"
    echo ""
    echo "4. Click 'Generate a new client secret' and copy the secret"
    echo "   (Note: GitHub only shows the secret once when generated)"
    echo ""
    echo "5. Add these values to deploy/config.env:"
    echo -e "   ${GREEN}GITHUB_OAUTH_CLIENT_ID=your-client-id${NC}"
    echo -e "   ${GREEN}GITHUB_OAUTH_CLIENT_SECRET=your-client-secret${NC}"
    echo ""
    echo "6. Run this deployment script again"
    echo ""
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 1
fi

GITHUB_PROVIDER_NAME="github-provider-${DEPLOYMENT_ENV:-prod}"

# Check if GitHub provider already exists
EXISTING_GITHUB_PROVIDER=$(aws bedrock-agentcore-control list-oauth2-credential-providers \
    --region "${AWS_REGION}" \
    --query "oauth2CredentialProviderSummaries[?name=='${GITHUB_PROVIDER_NAME}'].oauth2CredentialProviderId" \
    --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_GITHUB_PROVIDER" ]; then
    echo -e "${GREEN}✓${NC} GitHub OAuth provider already exists: ${EXISTING_GITHUB_PROVIDER}"

    # Update existing provider
    echo -e "${YELLOW}Updating GitHub OAuth provider...${NC}"
    aws bedrock-agentcore-control update-oauth2-credential-provider \
        --oauth2-credential-provider-id "${EXISTING_GITHUB_PROVIDER}" \
        --region "${AWS_REGION}" \
        --oauth2-provider-config-input "githubOauth2ProviderConfig={clientId=${GITHUB_OAUTH_CLIENT_ID},clientSecret=${GITHUB_OAUTH_CLIENT_SECRET}}" \
        --output json > /dev/null 2>&1 || echo -e "${YELLOW}Warning: Could not update GitHub provider${NC}"
else
    echo -e "${YELLOW}Creating GitHub OAuth provider: ${GITHUB_PROVIDER_NAME}${NC}"

    GITHUB_PROVIDER_OUTPUT=$(aws bedrock-agentcore-control create-oauth2-credential-provider \
        --name "${GITHUB_PROVIDER_NAME}" \
        --credential-provider-vendor "GithubOauth2" \
        --oauth2-provider-config-input "githubOauth2ProviderConfig={clientId=${GITHUB_OAUTH_CLIENT_ID},clientSecret=${GITHUB_OAUTH_CLIENT_SECRET}}" \
        --region "${AWS_REGION}" \
        --output json 2>&1)

    if [ $? -eq 0 ]; then
        GITHUB_PROVIDER_ID=$(echo "$GITHUB_PROVIDER_OUTPUT" | jq -r '.oauth2CredentialProviderId')
        echo -e "${GREEN}✓${NC} GitHub OAuth provider created: ${GITHUB_PROVIDER_ID}"
    else
        echo -e "${YELLOW}Warning: Could not create GitHub provider${NC}"
        echo "$GITHUB_PROVIDER_OUTPUT" | grep -i error || true
    fi
fi

echo ""
echo -e "${GREEN}Step 2 Complete!${NC}"
echo "AgentCore Runtime ARN: ${RUNTIME_ARN}"

if [ -n "$COGNITO_USER_POOL_ID" ]; then
    echo ""
    echo -e "${GREEN}Cognito Configuration (save to config.env for future use):${NC}"
    echo "  COGNITO_USER_POOL_ID=${COGNITO_USER_POOL_ID}"
    echo "  COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}"
    echo "  COGNITO_DISCOVERY_URL=${COGNITO_DISCOVERY_URL}"
    echo "  COGNITO_REGION=${AWS_REGION}"
fi
echo ""
