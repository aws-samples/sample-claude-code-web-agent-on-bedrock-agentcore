#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.env"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Step 1: Build and Push Docker Image to ECR${NC}"
echo "=============================================="

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${YELLOW}AWS_ACCOUNT_ID not set in config, detecting...${NC}"
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    echo -e "${GREEN}Detected AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}${NC}"
fi

if [ -z "$AWS_REGION" ]; then
    echo -e "${YELLOW}AWS_REGION not set, using default...${NC}"
    AWS_REGION=$(aws configure get region)
    AWS_REGION=${AWS_REGION:-us-west-2}
    echo -e "${GREEN}Using AWS_REGION: ${AWS_REGION}${NC}"
fi

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
FULL_IMAGE_NAME="${ECR_URI}/${ECR_REPOSITORY_NAME}:${DOCKER_IMAGE_VERSION}"

echo "Configuration:"
echo "  ECR Repository: ${ECR_REPOSITORY_NAME}"
echo "  Image Version: ${DOCKER_IMAGE_VERSION}"
echo "  Full Image URI: ${FULL_IMAGE_NAME}"
echo ""

echo -e "${YELLOW}Checking if ECR repository exists...${NC}"
if ! aws ecr describe-repositories --region "${AWS_REGION}" --repository-names "${ECR_REPOSITORY_NAME}" > /dev/null 2>&1; then
    echo -e "${YELLOW}Creating ECR repository: ${ECR_REPOSITORY_NAME}${NC}"
    aws ecr create-repository \
        --region "${AWS_REGION}" \
        --repository-name "${ECR_REPOSITORY_NAME}" \
        --image-scanning-configuration scanOnPush=true \
        --tags \
            Key=Project,Value="${TAG_PROJECT}" \
            Key=Environment,Value="${TAG_ENVIRONMENT}" \
            Key=ManagedBy,Value="${TAG_MANAGED_BY}" \
        > /dev/null
    echo -e "${GREEN}✓${NC} ECR repository created"
else
    echo -e "${GREEN}✓${NC} ECR repository already exists"
fi

echo -e "${YELLOW}Logging into ECR...${NC}"
aws ecr get-login-password --region "${AWS_REGION}" | \
    docker login --username AWS --password-stdin "${ECR_URI}"
echo -e "${GREEN}✓${NC} Logged into ECR"

echo -e "${YELLOW}Building Docker image for ARM64 architecture...${NC}"
docker build --platform linux/arm64 -t "${FULL_IMAGE_NAME}" -f "${SCRIPT_DIR}/Dockerfile" "${SCRIPT_DIR}/.."
echo -e "${GREEN}✓${NC} Docker image built (ARM64)"

echo -e "${YELLOW}Pushing image to ECR...${NC}"
docker push "${FULL_IMAGE_NAME}"
echo -e "${GREEN}✓${NC} Image pushed to ECR"

echo ""
echo -e "${GREEN}Step 1 Complete!${NC}"
echo "Image URI: ${FULL_IMAGE_NAME}"
echo ""
echo "export DOCKER_IMAGE_URI=${FULL_IMAGE_NAME}" > "${SCRIPT_DIR}/.build_output"
