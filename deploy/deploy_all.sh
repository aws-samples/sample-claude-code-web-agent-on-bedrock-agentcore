#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "========================================"
echo "  Claude Agent API Server Deployment"
echo "========================================"
echo -e "${NC}"

if [ ! -f "${SCRIPT_DIR}/config.env" ]; then
    echo -e "${RED}Error: config.env not found${NC}"
    echo "Please create config.env from config.env.template:"
    echo "  cp ${SCRIPT_DIR}/config.env.template ${SCRIPT_DIR}/config.env"
    echo "  # Edit config.env with your values"
    exit 1
fi

echo -e "${YELLOW}Loading configuration...${NC}"
source "${SCRIPT_DIR}/config.env"
echo -e "${GREEN}✓${NC} Configuration loaded"
echo ""

REQUIRED_VARS=(
    "AWS_REGION"
    "ECR_REPOSITORY_NAME"
    "AGENT_RUNTIME_NAME"
    "IAM_ROLE_NAME"
    "S3_WORKSPACE_BUCKET"
    "AMPLIFY_APP_NAME"
)

echo -e "${YELLOW}Validating configuration...${NC}"
MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${RED}Error: Missing required configuration variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please update config.env with the required values"
    exit 1
fi

echo -e "${GREEN}✓${NC} Configuration validated"
echo ""

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is not installed${NC}"
    echo "Please install jq:"
    echo "  macOS: brew install jq"
    echo "  Ubuntu: sudo apt-get install jq"
    exit 1
fi

echo -e "${GREEN}✓${NC} All required tools are installed"
echo ""

if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials not configured or invalid${NC}"
    echo "Please run: aws configure"
    exit 1
fi

echo -e "${GREEN}✓${NC} AWS credentials validated"
echo ""

START_TIME=$(date +%s)

echo -e "${BLUE}Starting deployment process...${NC}"
echo ""

echo -e "${BLUE}================================================================${NC}"
bash "${SCRIPT_DIR}/01_build_and_push.sh"
echo -e "${BLUE}================================================================${NC}"
echo ""

echo -e "${BLUE}================================================================${NC}"
bash "${SCRIPT_DIR}/02_deploy_agentcore.sh"
echo -e "${BLUE}================================================================${NC}"
echo ""

echo -e "${BLUE}================================================================${NC}"
bash "${SCRIPT_DIR}/03_deploy_amplify.sh"
echo -e "${BLUE}================================================================${NC}"
echo ""

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

if [ -f "${SCRIPT_DIR}/.agentcore_output" ]; then
    source "${SCRIPT_DIR}/.agentcore_output"
fi

if [ -f "${SCRIPT_DIR}/.amplify_output" ]; then
    source "${SCRIPT_DIR}/.amplify_output"
fi

echo -e "${GREEN}"
echo "========================================"
echo "  Deployment Complete!"
echo "========================================"
echo -e "${NC}"
echo "Total time: ${MINUTES}m ${SECONDS}s"
echo ""
echo -e "${GREEN}Deployment Summary:${NC}"
echo "-------------------------------------------"
echo -e "${YELLOW}Docker Image:${NC}"
if [ -f "${SCRIPT_DIR}/.build_output" ]; then
    source "${SCRIPT_DIR}/.build_output"
    echo "  URI: ${DOCKER_IMAGE_URI}"
fi
echo ""
echo -e "${YELLOW}AgentCore Runtime:${NC}"
if [ -n "$AGENT_RUNTIME_ARN" ]; then
    echo "  ARN: ${AGENT_RUNTIME_ARN}"
    echo "  IAM Role: ${IAM_ROLE_ARN}"
    echo "  S3 Bucket: ${S3_WORKSPACE_BUCKET}"
fi
echo ""
echo -e "${YELLOW}Amplify Frontend:${NC}"
if [ -n "$AMPLIFY_APP_URL" ]; then
    echo "  URL: ${AMPLIFY_APP_URL}"
    echo "  App ID: ${AMPLIFY_APP_ID}"
fi
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "1. Access your application at: ${AMPLIFY_APP_URL}"
echo "2. Monitor AgentCore Runtime logs in CloudWatch"
echo "3. Configure custom domain in Amplify (optional)"
echo "4. Set up GitHub integration for CI/CD (optional)"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  View logs: aws logs tail /aws/bedrock-agentcore/runtimes/${AGENT_RUNTIME_NAME} --follow"
echo "  Update config: vi ${SCRIPT_DIR}/config.env && ./deploy_all.sh"
echo "  Clean up: ./cleanup.sh"
echo ""
