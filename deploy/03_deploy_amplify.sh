#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.env"

if [ -f "${SCRIPT_DIR}/.agentcore_output" ]; then
    source "${SCRIPT_DIR}/.agentcore_output"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Step 3: Deploy Amplify Frontend${NC}"
echo "========================================"

if [ -z "$AWS_REGION" ]; then
    AWS_REGION=$(aws configure get region)
    AWS_REGION=${AWS_REGION:-us-west-2}
fi

echo "Configuration:"
echo "  App Name: ${AMPLIFY_APP_NAME}"
echo "  Branch: ${AMPLIFY_BRANCH_NAME}"
echo "  Region: ${AWS_REGION}"
echo ""

if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is not installed${NC}"
    echo "Please install jq:"
    echo "  macOS: brew install jq"
    echo "  Ubuntu: sudo apt-get install jq"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    echo "Please install Node.js (version 18 or later):"
    echo "  macOS: brew install node"
    echo "  Ubuntu: sudo apt-get install nodejs npm"
    echo "  Or visit: https://nodejs.org/"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed${NC}"
    echo "Please install npm:"
    echo "  macOS: brew install node"
    echo "  Ubuntu: sudo apt-get install npm"
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo -e "${RED}Error: Node.js version 18 or later is required${NC}"
    echo "Current version: $(node --version)"
    echo "Please upgrade Node.js"
    exit 1
fi

echo -e "${GREEN}✓${NC} Node.js $(node --version) and npm $(npm --version) installed"

if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials not configured${NC}"
    echo "Please run: aws configure"
    exit 1
fi

echo -e "${GREEN}✓${NC} AWS CLI configured"

APP_ID=$(aws amplify list-apps --region "$AWS_REGION" --query "apps[?name=='$AMPLIFY_APP_NAME'].appId" --output text 2>/dev/null || echo "")

if [ -z "$APP_ID" ]; then
    echo -e "${YELLOW}Creating new Amplify app: $AMPLIFY_APP_NAME${NC}"

    CREATE_OUTPUT=$(aws amplify create-app \
        --name "$AMPLIFY_APP_NAME" \
        --region "$AWS_REGION" \
        --platform WEB \
        --build-spec file://"${SCRIPT_DIR}/amplify.yml" \
        --custom-rules '[
            {
                "source": "</^[^.]+$|\\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp)$)([^.]+$)/>",
                "target": "/index.html",
                "status": "200"
            }
        ]' \
        --tags \
            Project="${TAG_PROJECT}" \
        --output json)

    APP_ID=$(echo "$CREATE_OUTPUT" | jq -r '.app.appId')
    echo -e "${GREEN}✓${NC} Created Amplify app with ID: $APP_ID"
    IS_NEW_APP=true
else
    echo -e "${GREEN}✓${NC} Found existing Amplify app with ID: $APP_ID"
    IS_NEW_APP=false
fi

echo -e "${YELLOW}Updating SPA redirect rules...${NC}"
aws amplify update-app \
    --app-id "$APP_ID" \
    --region "$AWS_REGION" \
    --custom-rules '[
        {
            "source": "</^[^.]+$|\\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp)$)([^.]+$)/>",
            "target": "/index.html",
            "status": "200"
        }
    ]' \
    > /dev/null 2>&1 || echo -e "${YELLOW}Note: Could not update custom rules via CLI${NC}"

echo -e "${GREEN}✓${NC} Redirect rules configured"

echo -e "${YELLOW}Configuring environment variables...${NC}"

ENV_VARS_JSON="{"
if [ -f "${SCRIPT_DIR}/../web_client/.env" ]; then
    while IFS='=' read -r key value; do
        if [[ ! "$key" =~ ^# ]] && [ -n "$key" ]; then
            value=$(echo "$value" | sed 's/^"\(.*\)"$/\1/')
            ENV_VARS_JSON="${ENV_VARS_JSON}\"$key\": \"$value\","
        fi
    done < "${SCRIPT_DIR}/../web_client/.env"
fi

if [ -n "$AGENT_RUNTIME_ARN" ]; then
    ENV_VARS_JSON="${ENV_VARS_JSON}\"VITE_AGENT_RUNTIME_ARN\": \"$AGENT_RUNTIME_ARN\","
fi

ENV_VARS_JSON="${ENV_VARS_JSON%,}}"

aws amplify update-app \
    --app-id "$APP_ID" \
    --region "$AWS_REGION" \
    --environment-variables "$ENV_VARS_JSON" \
    > /dev/null

echo -e "${GREEN}✓${NC} Environment variables configured"

echo -e "${YELLOW}Updating web client configuration...${NC}"
cd "${SCRIPT_DIR}/../web_client"

# Update .env file with AgentCore configuration
if [ -f "${SCRIPT_DIR}/.agentcore_output" ]; then
    source "${SCRIPT_DIR}/.agentcore_output"

    # Backup original .env
    cp .env .env.backup 2>/dev/null || true

    # Update or add VITE_DEFAULT_SERVER_URL
    if [ -n "$AGENT_RUNTIME_URL" ]; then
        if grep -q "^VITE_DEFAULT_SERVER_URL=" .env; then
            sed -i.bak "s|^VITE_DEFAULT_SERVER_URL=.*|VITE_DEFAULT_SERVER_URL=\"${AGENT_RUNTIME_URL}\"|" .env
        else
            echo "VITE_DEFAULT_SERVER_URL=\"${AGENT_RUNTIME_URL}\"" >> .env
        fi
        echo "  ✓ Updated VITE_DEFAULT_SERVER_URL"
    fi

    # Update Cognito configuration
    if [ -n "$COGNITO_REGION" ]; then
        if grep -q "^VITE_COGNITO_REGION=" .env; then
            sed -i.bak "s|^VITE_COGNITO_REGION=.*|VITE_COGNITO_REGION=${COGNITO_REGION}|" .env
        else
            echo "VITE_COGNITO_REGION=${COGNITO_REGION}" >> .env
        fi
        echo "  ✓ Updated VITE_COGNITO_REGION"
    fi

    if [ -n "$COGNITO_USER_POOL_ID" ]; then
        if grep -q "^VITE_COGNITO_USER_POOL_ID=" .env; then
            sed -i.bak "s|^VITE_COGNITO_USER_POOL_ID=.*|VITE_COGNITO_USER_POOL_ID=${COGNITO_USER_POOL_ID}|" .env
        else
            echo "VITE_COGNITO_USER_POOL_ID=${COGNITO_USER_POOL_ID}" >> .env
        fi
        echo "  ✓ Updated VITE_COGNITO_USER_POOL_ID"
    fi

    if [ -n "$COGNITO_CLIENT_ID" ]; then
        if grep -q "^VITE_COGNITO_CLIENT_ID=" .env; then
            sed -i.bak "s|^VITE_COGNITO_CLIENT_ID=.*|VITE_COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}|" .env
        else
            echo "VITE_COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}" >> .env
        fi
        echo "  ✓ Updated VITE_COGNITO_CLIENT_ID"
    fi

    # Enable invocations mode by default
    if grep -q "^VITE_USE_INVOCATIONS=" .env; then
        sed -i.bak "s|^VITE_USE_INVOCATIONS=.*|VITE_USE_INVOCATIONS=true|" .env
    else
        echo "VITE_USE_INVOCATIONS=true" >> .env
    fi
    echo "  ✓ Set VITE_USE_INVOCATIONS=true"

    # Set available model list
    AVAILABLE_MODELS="global.anthropic.claude-sonnet-4-5-20250929-v1:0,global.anthropic.claude-haiku-4-5-20251001-v1:0,qwen.qwen3-coder-480b-a35b-v1:0"
    if grep -q "^VITE_AVAILABLE_MODELS=" .env; then
        sed -i.bak "s|^VITE_AVAILABLE_MODELS=.*|VITE_AVAILABLE_MODELS=\"${AVAILABLE_MODELS}\"|" .env
    else
        echo "VITE_AVAILABLE_MODELS=\"${AVAILABLE_MODELS}\"" >> .env
    fi
    echo "  ✓ Set VITE_AVAILABLE_MODELS"

    # Hide settings button by default
    if grep -q "^VITE_HIDE_SETTINGS_BUTTON=" .env; then
        sed -i.bak "s|^VITE_HIDE_SETTINGS_BUTTON=.*|VITE_HIDE_SETTINGS_BUTTON=true|" .env
    else
        echo "VITE_HIDE_SETTINGS_BUTTON=true" >> .env
    fi
    echo "  ✓ Set VITE_HIDE_SETTINGS_BUTTON=true"

    # Clean up backup files
    rm -f .env.bak
fi

echo -e "${GREEN}✓${NC} Web client configuration updated"

echo -e "${YELLOW}Installing web client dependencies...${NC}"

if [ ! -d "node_modules" ]; then
    echo "Installing npm packages..."
    npm install
else
    echo "node_modules exists, updating dependencies..."
    npm install
fi

echo -e "${GREEN}✓${NC} Dependencies installed"

echo -e "${YELLOW}Building web client...${NC}"
npm run build
cd "${SCRIPT_DIR}"

echo -e "${GREEN}✓${NC} Build complete"

BRANCH_EXISTS=$(aws amplify list-branches \
    --app-id "$APP_ID" \
    --region "$AWS_REGION" \
    --query "branches[?branchName=='$AMPLIFY_BRANCH_NAME'].branchName" \
    --output text 2>/dev/null || echo "")

if [ -z "$BRANCH_EXISTS" ]; then
    echo -e "${YELLOW}Creating branch: $AMPLIFY_BRANCH_NAME${NC}"
    aws amplify create-branch \
        --app-id "$APP_ID" \
        --branch-name "$AMPLIFY_BRANCH_NAME" \
        --region "$AWS_REGION" \
        > /dev/null
    echo -e "${GREEN}✓${NC} Branch created"
fi

echo -e "${YELLOW}Checking for pending/running jobs...${NC}"
PENDING_JOBS=$(aws amplify list-jobs \
    --app-id "$APP_ID" \
    --branch-name "$AMPLIFY_BRANCH_NAME" \
    --region "$AWS_REGION" \
    --max-results 10 \
    --output json 2>/dev/null | jq -r '.jobSummaries[] | select(.status=="PENDING" or .status=="RUNNING") | .jobId' || echo "")

if [ -n "$PENDING_JOBS" ]; then
    echo "Found pending/running jobs, cleaning up..."
    for job_id in $PENDING_JOBS; do
        echo "  Stopping job $job_id..."
        aws amplify stop-job \
            --app-id "$APP_ID" \
            --branch-name "$AMPLIFY_BRANCH_NAME" \
            --job-id "$job_id" \
            --region "$AWS_REGION" \
            > /dev/null 2>&1 || true
    done
    echo -e "${GREEN}✓${NC} Cleaned up pending/running jobs"
else
    echo -e "${GREEN}✓${NC} No pending/running jobs found"
fi

echo -e "${YELLOW}Creating deployment...${NC}"

DEPLOYMENT=$(aws amplify create-deployment \
    --app-id "$APP_ID" \
    --branch-name "$AMPLIFY_BRANCH_NAME" \
    --region "$AWS_REGION" \
    --output json 2>&1)

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to create deployment${NC}"
    echo "$DEPLOYMENT"
    exit 1
fi

ZIP_UPLOAD_URL=$(echo "$DEPLOYMENT" | jq -r '.zipUploadUrl')
JOB_ID=$(echo "$DEPLOYMENT" | jq -r '.jobId')

echo -e "${GREEN}✓${NC} Deployment created (Job ID: $JOB_ID)"

echo -e "${YELLOW}Creating deployment package...${NC}"
cd "${SCRIPT_DIR}/../web_client/dist"
zip -r "${SCRIPT_DIR}/deployment.zip" . > /dev/null
cd "${SCRIPT_DIR}"

echo -e "${GREEN}✓${NC} Package created"

echo -e "${YELLOW}Uploading to Amplify...${NC}"
UPLOAD_RESPONSE=$(curl -X PUT "$ZIP_UPLOAD_URL" \
    -H "Content-Type: application/zip" \
    --data-binary @deployment.zip \
    --write-out "%{http_code}" \
    --silent \
    --output /tmp/amplify_upload_response.txt)

if [ "$UPLOAD_RESPONSE" != "200" ]; then
    echo -e "${RED}Error: Upload failed with HTTP code $UPLOAD_RESPONSE${NC}"
    cat /tmp/amplify_upload_response.txt
    rm /tmp/amplify_upload_response.txt
    exit 1
fi

rm -f /tmp/amplify_upload_response.txt
echo -e "${GREEN}✓${NC} Upload complete (HTTP $UPLOAD_RESPONSE)"

echo -e "${YELLOW}Starting deployment...${NC}"
START_RESULT=$(aws amplify start-deployment \
    --app-id "$APP_ID" \
    --branch-name "$AMPLIFY_BRANCH_NAME" \
    --job-id "$JOB_ID" \
    --region "$AWS_REGION" \
    --output json 2>&1)

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to start deployment${NC}"
    echo "$START_RESULT"
    rm deployment.zip
    exit 1
fi

echo -e "${GREEN}✓${NC} Deployment started successfully"

rm deployment.zip

DEFAULT_DOMAIN=$(aws amplify get-app \
    --app-id "$APP_ID" \
    --region "$AWS_REGION" \
    --query "app.defaultDomain" \
    --output text)

APP_URL="https://${AMPLIFY_BRANCH_NAME}.${DEFAULT_DOMAIN}"

echo ""
echo -e "${GREEN}Step 3 Complete!${NC}"
echo "========================================"
echo "App ID: $APP_ID"
echo "Branch: $AMPLIFY_BRANCH_NAME"
echo "Job ID: $JOB_ID"
echo "URL: $APP_URL"
echo ""
echo "Monitor deployment status:"
echo "https://console.aws.amazon.com/amplify/home?region=$AWS_REGION#/$APP_ID/$AMPLIFY_BRANCH_NAME/$JOB_ID"
echo ""

echo "export AMPLIFY_APP_ID=${APP_ID}" > "${SCRIPT_DIR}/.amplify_output"
echo "export AMPLIFY_APP_URL=${APP_URL}" >> "${SCRIPT_DIR}/.amplify_output"

if [ "$IS_NEW_APP" = true ]; then
    echo -e "${YELLOW}Optional: Connect GitHub for Continuous Deployment${NC}"
    echo "1. Open: https://console.aws.amazon.com/amplify/home?region=$AWS_REGION#/$APP_ID"
    echo "2. Click 'Connect branch'"
    echo "3. Select GitHub and authorize"
    echo "4. Repository: $GITHUB_REPO"
    echo "5. Branch: $AMPLIFY_BRANCH_NAME"
    echo ""
fi
