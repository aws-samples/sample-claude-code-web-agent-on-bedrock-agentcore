#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}"
echo "========================================"
echo "  Claude Agent Cleanup Script"
echo "========================================"
echo -e "${NC}"
echo -e "${YELLOW}WARNING: This will delete all deployed resources!${NC}"
echo ""

if [ ! -f "${SCRIPT_DIR}/config.env" ]; then
    echo -e "${RED}Error: config.env not found${NC}"
    exit 1
fi

source "${SCRIPT_DIR}/config.env"

if [ -f "${SCRIPT_DIR}/.build_output" ]; then
    source "${SCRIPT_DIR}/.build_output"
fi

if [ -f "${SCRIPT_DIR}/.agentcore_output" ]; then
    source "${SCRIPT_DIR}/.agentcore_output"
fi

if [ -f "${SCRIPT_DIR}/.amplify_output" ]; then
    source "${SCRIPT_DIR}/.amplify_output"
fi

if [ -z "$AWS_REGION" ]; then
    AWS_REGION=$(aws configure get region)
    AWS_REGION=${AWS_REGION:-us-west-2}
fi

if [ -z "$AWS_ACCOUNT_ID" ]; then
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
fi

echo "Configuration:"
echo "  Region: ${AWS_REGION}"
echo "  Account: ${AWS_ACCOUNT_ID}"
echo "  ECR Repository: ${ECR_REPOSITORY_NAME}"
echo "  Agent Runtime: ${AGENT_RUNTIME_NAME}"
echo "  IAM Role: ${IAM_ROLE_NAME}"
echo "  S3 Bucket: ${S3_WORKSPACE_BUCKET}-${AWS_REGION}"
echo "  Amplify App: ${AMPLIFY_APP_NAME}"
echo ""

read -p "Are you sure you want to delete ALL resources? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cleanup cancelled"
    exit 0
fi

echo ""
echo -e "${YELLOW}Starting cleanup...${NC}"
echo ""

echo -e "${YELLOW}[1/5] Deleting Amplify app...${NC}"
if [ -n "$AMPLIFY_APP_ID" ]; then
    APP_ID="$AMPLIFY_APP_ID"
else
    APP_ID=$(aws amplify list-apps --region "$AWS_REGION" --query "apps[?name=='$AMPLIFY_APP_NAME'].appId" --output text 2>/dev/null || echo "")
fi

if [ -n "$APP_ID" ]; then
    echo "Deleting Amplify app: $APP_ID"
    aws amplify delete-app --app-id "$APP_ID" --region "$AWS_REGION" 2>/dev/null || echo "  Could not delete Amplify app"
    echo -e "${GREEN}✓${NC} Amplify app deleted"
else
    echo "  No Amplify app found"
fi

echo ""
echo -e "${YELLOW}[2/5] Deleting AgentCore Runtime...${NC}"
if [ -n "$AGENT_RUNTIME_ARN" ]; then
    RUNTIME_ID=$(echo "$AGENT_RUNTIME_ARN" | awk -F'/' '{print $NF}')
elif [ -n "$AGENT_RUNTIME_NAME" ]; then
    RUNTIMES=$(aws bedrock-agentcore-control list-agent-runtimes --region "$AWS_REGION" 2>/dev/null || echo "")
    RUNTIME_ID=$(echo "$RUNTIMES" | jq -r ".agentRuntimes[] | select(.agentRuntimeName==\"$AGENT_RUNTIME_NAME\") | .agentRuntimeId" 2>/dev/null || echo "")
else
    RUNTIME_ID=""
fi

if [ -n "$RUNTIME_ID" ]; then
    echo "Deleting AgentCore Runtime: $RUNTIME_ID"
    aws bedrock-agentcore-control delete-agent-runtime \
        --agent-runtime-id "$RUNTIME_ID" \
        --region "$AWS_REGION" 2>/dev/null || echo "  Could not delete AgentCore Runtime"
    echo -e "${GREEN}✓${NC} AgentCore Runtime deleted"
else
    echo "  No AgentCore Runtime found"
fi

echo ""
echo -e "${YELLOW}[3/5] Deleting Cognito resources...${NC}"

if [ -n "$COGNITO_USER_POOL_ID" ]; then
    POOL_ID="$COGNITO_USER_POOL_ID"
elif [ -n "$COGNITO_DISCOVERY_URL" ]; then
    POOL_ID=$(echo "$COGNITO_DISCOVERY_URL" | grep -oP 'us-west-2_[A-Za-z0-9]+')
else
    POOL_ID=""
fi

if [ -n "$POOL_ID" ]; then
    echo "Found Cognito User Pool: $POOL_ID"
    read -p "Do you want to delete Cognito User Pool and App Client? (yes/no): " DELETE_COGNITO

    if [ "$DELETE_COGNITO" == "yes" ]; then
        echo "Listing app clients..."
        APP_CLIENTS=$(aws cognito-idp list-user-pool-clients --user-pool-id "$POOL_ID" --region "$AWS_REGION" --query 'UserPoolClients[].ClientId' --output text 2>/dev/null || echo "")

        for client_id in $APP_CLIENTS; do
            echo "  Deleting app client: $client_id"
            aws cognito-idp delete-user-pool-client --user-pool-id "$POOL_ID" --client-id "$client_id" --region "$AWS_REGION" 2>/dev/null || true
        done

        echo "  Deleting user pool: $POOL_ID"
        aws cognito-idp delete-user-pool --user-pool-id "$POOL_ID" --region "$AWS_REGION" 2>/dev/null || echo "  Could not delete Cognito User Pool"
        echo -e "${GREEN}✓${NC} Cognito resources deleted"
    else
        echo "  Skipping Cognito deletion"
    fi
else
    echo "  No Cognito User Pool found in configuration"
fi

echo ""
echo -e "${YELLOW}[4/6] Deleting IAM role...${NC}"
FULL_ROLE_NAME="${IAM_ROLE_NAME}-${AWS_REGION}-${DEPLOYMENT_ENV:-prod}"

if aws iam get-role --role-name "$FULL_ROLE_NAME" &>/dev/null; then
    echo "Deleting IAM role policies: $FULL_ROLE_NAME"

    POLICIES=$(aws iam list-role-policies --role-name "$FULL_ROLE_NAME" --query 'PolicyNames' --output text 2>/dev/null || echo "")
    for policy in $POLICIES; do
        echo "  Deleting inline policy: $policy"
        aws iam delete-role-policy --role-name "$FULL_ROLE_NAME" --policy-name "$policy" 2>/dev/null || true
    done

    ATTACHED_POLICIES=$(aws iam list-attached-role-policies --role-name "$FULL_ROLE_NAME" --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null || echo "")
    for policy_arn in $ATTACHED_POLICIES; do
        echo "  Detaching managed policy: $policy_arn"
        aws iam detach-role-policy --role-name "$FULL_ROLE_NAME" --policy-arn "$policy_arn" 2>/dev/null || true
    done

    echo "  Deleting role: $FULL_ROLE_NAME"
    aws iam delete-role --role-name "$FULL_ROLE_NAME" 2>/dev/null || echo "  Could not delete IAM role"
    echo -e "${GREEN}✓${NC} IAM role deleted"
else
    echo "  No IAM role found"
fi

echo ""
echo -e "${YELLOW}[5/6] Deleting S3 bucket...${NC}"
BUCKET_PREFIX="${S3_WORKSPACE_BUCKET_PREFIX:-agentcore}"
BUCKET_NAME="${BUCKET_PREFIX}-${AWS_REGION}-${AWS_ACCOUNT_ID}"

if aws s3 ls "s3://$BUCKET_NAME" &>/dev/null; then
    echo "Emptying S3 bucket: $BUCKET_NAME"
    aws s3 rm "s3://$BUCKET_NAME" --recursive 2>/dev/null || true

    echo "Deleting S3 bucket: $BUCKET_NAME"
    aws s3api delete-bucket --bucket "$BUCKET_NAME" --region "$AWS_REGION" 2>/dev/null || echo "  Could not delete S3 bucket"
    echo -e "${GREEN}✓${NC} S3 bucket deleted"
else
    echo "  No S3 bucket found"
fi

echo ""
echo -e "${YELLOW}[6/6] Cleaning up ECR repository...${NC}"

read -p "Do you want to delete the ECR repository and all images? (yes/no): " DELETE_ECR

if [ "$DELETE_ECR" == "yes" ]; then
    if aws ecr describe-repositories --region "$AWS_REGION" --repository-names "$ECR_REPOSITORY_NAME" &>/dev/null; then
        echo "Deleting ECR repository: $ECR_REPOSITORY_NAME"
        aws ecr delete-repository \
            --repository-name "$ECR_REPOSITORY_NAME" \
            --region "$AWS_REGION" \
            --force 2>/dev/null || echo "  Could not delete ECR repository"
        echo -e "${GREEN}✓${NC} ECR repository deleted"
    else
        echo "  No ECR repository found"
    fi
else
    echo "  Skipping ECR repository deletion"
fi

echo ""
echo -e "${YELLOW}Cleaning up local state files...${NC}"
rm -f "${SCRIPT_DIR}/.build_output"
rm -f "${SCRIPT_DIR}/.agentcore_output"
rm -f "${SCRIPT_DIR}/.amplify_output"
echo -e "${GREEN}✓${NC} Local state files cleaned"

echo ""
echo -e "${GREEN}"
echo "========================================"
echo "  Cleanup Complete!"
echo "========================================"
echo -e "${NC}"
echo "All resources have been deleted."
echo ""
echo -e "${YELLOW}Note:${NC}"
echo "- CloudWatch Logs may still exist and will incur minimal costs"
echo "- To delete logs manually:"
echo "  aws logs delete-log-group --log-group-name /aws/bedrock-agentcore/runtimes/${AGENT_RUNTIME_NAME}"
echo ""
