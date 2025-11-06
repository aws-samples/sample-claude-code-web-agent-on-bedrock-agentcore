# Claude Agent API Server Docker Environment

This directory contains Docker configuration for running the Claude Agent API Server in an isolated environment.

## Prerequisites

- Docker installed on your system
- Docker Compose (optional, for easier management)
- Anthropic API key

## Quick Start

### Option 1: Using the Test Script (Recommended)

The easiest way to build and test the Docker container:

```bash
cd docker
./test_docker.sh
```

This script will:
1. Clean up any existing containers
2. Build the Docker image
3. Start the container on port 8080
4. Test all API endpoints
5. Display container information

### Option 2: Using Docker Compose

```bash
# Set your API key
export ANTHROPIC_API_KEY=your_api_key_here

# Build and start the container
cd docker
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Option 3: Using Docker directly

```bash
# Build the image
cd docker
docker build -t claude-agent-api-server:latest -f Dockerfile ..

# Run the container
docker run -d \
  --name claude-agent-api-server \
  -p 8080:8080 \
  -e ANTHROPIC_API_KEY=your_api_key_here \
  claude-agent-api-server:latest

# Check logs
docker logs -f claude-agent-api-server

# Stop and remove
docker stop claude-agent-api-server
docker rm claude-agent-api-server
```

## API Endpoints

Once the container is running, you can access:

- **Health Check**: http://localhost:8080/health
- **API Documentation**: http://localhost:8080/docs
- **OpenAPI Spec**: http://localhost:8080/openapi.json

### Example API Usage

```bash
# Health check
curl http://localhost:8080/health

# Create a session
curl -X POST http://localhost:8080/sessions

# Send a message (replace SESSION_ID)
curl -X POST http://localhost:8080/sessions/SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello, Claude!"}'
```

## Directory Structure

```
docker/
├── Dockerfile          # Docker image definition
├── docker-compose.yml  # Docker Compose configuration
├── test_docker.sh      # Automated test script
├── .env.example        # Environment variables example
└── README.md          # This file
```

## Technical Details

### Base Image
- Node.js Trixie (Debian Trixie)
- Python 3.12+
- UV package manager

### Installation Process
1. Installs system dependencies (curl, python3)
2. Installs UV package manager via official installer
3. Copies project files
4. Installs Python dependencies using `uv sync`
5. Starts FastAPI server on port 8080

### Environment Variables

- `ANTHROPIC_API_KEY`: Your Anthropic API key (required)
- `PYTHONUNBUFFERED`: Set to 1 for real-time logs

## Development

### Building Locally

```bash
# Build without cache
docker build --no-cache -t claude-agent-api-server:latest -f docker/Dockerfile .

# Build with specific tag
docker build -t claude-agent-api-server:v1.0.0 -f docker/Dockerfile .
```

### Debugging

```bash
# Access container shell
docker exec -it claude-agent-api-server bash

# View logs
docker logs claude-agent-api-server

# Follow logs in real-time
docker logs -f claude-agent-api-server

# Check container resource usage
docker stats claude-agent-api-server
```

## Troubleshooting

### Container fails to start
- Check if port 8080 is already in use: `lsof -i :8080`
- View container logs: `docker logs claude-agent-api-server`
- Verify API key is set correctly

### Server not responding
- Wait 10-15 seconds for server to initialize
- Check health endpoint: `curl http://localhost:8080/health`
- Verify container is running: `docker ps`

### Build failures
- Ensure you're building from the correct directory
- Check Docker has enough disk space
- Try building without cache: `docker build --no-cache`

## Stopping the Container

```bash
# Using Docker Compose
docker-compose down

# Using Docker directly
docker stop claude-agent-api-server
docker rm claude-agent-api-server
```
