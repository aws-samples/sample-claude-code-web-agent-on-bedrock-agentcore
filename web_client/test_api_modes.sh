#!/bin/bash
# Test script to verify both API modes work correctly

echo "======================================"
echo "API Modes Test Script"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to test a mode
test_mode() {
    local mode=$1
    local use_invocations=$2

    echo -e "${YELLOW}Testing $mode Mode${NC}"
    echo "Setting VITE_USE_INVOCATIONS=$use_invocations"

    # Update .env file
    echo "VITE_USE_INVOCATIONS=$use_invocations" > .env

    # Build the project
    echo "Building..."
    npm run build > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Build successful${NC}"
    else
        echo -e "${RED}✗ Build failed${NC}"
        return 1
    fi

    # Check if client.js was created correctly
    if [ -f "src/api/client.js" ]; then
        echo -e "${GREEN}✓ API client exists${NC}"
    else
        echo -e "${RED}✗ API client missing${NC}"
        return 1
    fi

    echo ""
}

# Backup existing .env
if [ -f ".env" ]; then
    cp .env .env.backup
    echo "Backed up existing .env file"
fi

# Test Direct Mode
test_mode "Direct" "false"

# Test Invocations Mode
test_mode "Invocations" "true"

# Restore backup
if [ -f ".env.backup" ]; then
    mv .env.backup .env
    echo "Restored original .env file"
fi

echo "======================================"
echo -e "${GREEN}All tests completed!${NC}"
echo "======================================"
echo ""
echo "Manual testing steps:"
echo "1. Start API server: uv run backend/server.py"
echo "2. Start web client: npm run dev"
echo "3. Check browser console for mode indicator:"
echo "   - 📡 Using Direct API mode"
echo "   - 🔀 Using Invocations API mode"
echo "4. Test session creation and messaging"
echo ""
