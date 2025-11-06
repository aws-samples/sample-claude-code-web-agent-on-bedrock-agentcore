# Workspace Management

This document describes workspace management features including Git repository cloning and S3 synchronization.

## Overview

The workspace management feature enables:
- **Git Clone**: Clone Git repositories directly into user workspaces
- **S3 Initialization**: Download user workspace from S3 to local filesystem
- **S3 Backup**: Upload local workspace back to S3
- **Workspace Info**: Get details about local workspace (size, file count, etc.)

This is particularly useful for:
- Setting up development environments from Git repositories
- Restoring user workspaces when starting new server instances
- Backing up work to S3 for persistence
- Sharing workspaces across multiple server instances
- Disaster recovery and data persistence

## Architecture

### S3 Path Structure

```
s3://{bucket}/{prefix}/{user_id}/{workspace_name}/
```

Example:
```
s3://my-workspace-bucket/user_data/user123/workspace/
├── project1/
│   ├── main.py
│   └── README.md
├── project2/
│   └── app.js
└── notes.txt
```

### Local Path Structure

```
{base_path}/{user_id}/
```

Example:
```
/workspace/user123/
├── project1/
│   ├── main.py
│   └── README.md
├── project2/
│   └── app.js
└── notes.txt
```

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Required: S3 bucket name
S3_WORKSPACE_BUCKET=my-workspace-bucket

# Optional: S3 key prefix (default: "user_data")
S3_WORKSPACE_PREFIX=user_data

# Optional: Local base path (default: "/workspace")
WORKSPACE_BASE_PATH=/workspace
```

### AWS Credentials

The server needs AWS credentials to access S3. Configure using one of:

1. **Environment Variables**:
   ```bash
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_REGION=us-west-2
   ```

2. **IAM Role** (recommended for EC2/ECS):
   - Attach IAM role with S3 permissions to your instance

3. **AWS Config Files**:
   - `~/.aws/credentials`
   - `~/.aws/config`

### Required IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-workspace-bucket",
        "arn:aws:s3:::my-workspace-bucket/*"
      ]
    }
  ]
}
```

## Prerequisites

### Install s5cmd

s5cmd is required for high-performance S3 transfers.

**Linux (x86_64)**:
```bash
# Download and install s5cmd
wget https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz
tar xzf s5cmd_2.2.2_Linux-64bit.tar.gz
sudo mv s5cmd /usr/local/bin/
sudo chmod +x /usr/local/bin/s5cmd

# Verify installation
s5cmd version
```

**macOS**:
```bash
brew install peak/tap/s5cmd
```

**From Source**:
```bash
go install github.com/peak/s5cmd/v2@latest
```

## API Endpoints

### 1. Clone Git Repository

**Endpoint**: `POST /workspace/clone-git`

**Description**: Clones a Git repository into a user's workspace directory.

**Request Body**:
```json
{
  "user_id": "user123",
  "git_url": "https://github.com/username/repository.git",
  "branch": "main",
  "repo_name": "my-project",
  "shallow": false
}
```

**Parameters**:
- `user_id` (string, required): User ID
- `git_url` (string, required): Git repository URL (HTTPS or SSH)
- `branch` (string, optional): Specific branch to clone (default: repository default branch)
- `repo_name` (string, optional): Custom name for cloned directory (default: extracted from URL)
- `shallow` (boolean, optional): Perform shallow clone with `--depth=1` for faster cloning (default: false)

**Response**:
```json
{
  "status": "success",
  "user_id": "user123",
  "git_url": "https://github.com/username/repository.git",
  "local_path": "/workspace/user123/my-project",
  "workspace_path": "/workspace/user123",
  "repo_name": "my-project",
  "branch": "main",
  "commit_hash": "abc123def456...",
  "shallow": false,
  "size_bytes": 5242880,
  "size_mb": 5.0,
  "message": "Successfully cloned repository to /workspace/user123/my-project",
  "output": "Cloning into '/workspace/user123/my-project'..."
}
```

**Example (cURL)**:
```bash
curl -X POST http://localhost:8000/workspace/clone-git \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "user_id": "user123",
    "git_url": "https://github.com/username/repository.git",
    "branch": "main",
    "shallow": true
  }'
```

**Example (Python)**:
```python
import httpx

response = httpx.post(
    "http://localhost:8000/workspace/clone-git",
    json={
        "user_id": "user123",
        "git_url": "https://github.com/username/repository.git",
        "branch": "main",
        "shallow": True  # Faster clone for large repositories
    }
)
print(response.json())
```

**Notes**:
- Requires `git` to be installed on the server
- Supports both HTTPS and SSH URLs
- SSH URLs require SSH keys to be configured
- Shallow clones (`--depth=1`) are faster but don't include full history
- Repository directory must not already exist
- Automatically cleans up on error

### 2. Initialize Workspace (Download from S3)

**Endpoint**: `POST /workspace/init`

**Description**: Downloads a user's workspace from S3 to local filesystem.

**Request Body**:
```json
{
  "user_id": "user123",
  "workspace_name": "workspace",
  "dry_run": false
}
```

**Parameters**:
- `user_id` (string, required): User ID
- `workspace_name` (string, optional): Workspace subdirectory name (default: "workspace")
- `dry_run` (boolean, optional): If true, simulates sync without transferring files (default: false)

**Response**:
```json
{
  "status": "success",
  "user_id": "user123",
  "s3_path": "s3://my-bucket/user_data/user123/workspace/*",
  "local_path": "/workspace/user123",
  "files_synced": 42,
  "dry_run": false,
  "message": "Successfully synced 42 files from S3",
  "output": "..."
}
```

**Example (cURL)**:
```bash
curl -X POST http://localhost:8000/workspace/init \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "user_id": "user123",
    "workspace_name": "workspace"
  }'
```

**Example (Python)**:
```python
import httpx

response = httpx.post(
    "http://localhost:8000/workspace/init",
    json={
        "user_id": "user123",
        "workspace_name": "workspace",
        "dry_run": False
    }
)
print(response.json())
```

### 2. Sync to S3 (Upload to S3)

**Endpoint**: `POST /workspace/sync-to-s3`

**Description**: Uploads a user's local workspace to S3.

**Request Body**:
```json
{
  "user_id": "user123",
  "workspace_name": "workspace",
  "dry_run": false
}
```

**Response**:
```json
{
  "status": "success",
  "user_id": "user123",
  "local_path": "/workspace/user123",
  "s3_path": "s3://my-bucket/user_data/user123/workspace/",
  "files_synced": 42,
  "dry_run": false,
  "message": "Successfully synced 42 files to S3",
  "output": "..."
}
```

**Example (cURL)**:
```bash
curl -X POST http://localhost:8000/workspace/sync-to-s3 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "user_id": "user123"
  }'
```

### 3. Get Workspace Info

**Endpoint**: `GET /workspace/info/{user_id}`

**Description**: Returns information about a user's local workspace.

**Parameters**:
- `user_id` (string, required): User ID (path parameter)

**Response**:
```json
{
  "exists": true,
  "path": "/workspace/user123",
  "size_bytes": 1048576,
  "size_mb": 1.0,
  "file_count": 42,
  "dir_count": 8
}
```

**Example (cURL)**:
```bash
curl http://localhost:8000/workspace/info/user123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Usage Patterns

### Pattern 1: Initialize on First Login

When a user first logs in or starts a new session:

```python
# 1. Check if workspace exists locally
info = httpx.get(f"http://localhost:8000/workspace/info/{user_id}")
workspace_info = info.json()

if not workspace_info["exists"]:
    # 2. Initialize workspace from S3
    response = httpx.post(
        "http://localhost:8000/workspace/init",
        json={"user_id": user_id}
    )
    print(f"Workspace initialized: {response.json()['message']}")
```

### Pattern 2: Periodic Backup

Periodically backup workspace to S3:

```python
import time

while True:
    # Backup every hour
    time.sleep(3600)

    response = httpx.post(
        "http://localhost:8000/workspace/sync-to-s3",
        json={"user_id": user_id}
    )
    print(f"Backup completed: {response.json()['message']}")
```

### Pattern 3: Pre-Flight Check (Dry Run)

Test sync before actually transferring files:

```python
# Dry run to see what would be transferred
response = httpx.post(
    "http://localhost:8000/workspace/init",
    json={
        "user_id": user_id,
        "dry_run": True
    }
)

result = response.json()
print(f"Would sync {result['files_synced']} files")
print(f"From: {result['s3_path']}")
print(f"To: {result['local_path']}")

# If acceptable, do the actual sync
if result['files_synced'] < 1000:
    response = httpx.post(
        "http://localhost:8000/workspace/init",
        json={"user_id": user_id}
    )
```

## Integration with Sessions

You can automatically initialize workspace when creating a session:

```python
# 1. Initialize workspace from S3
init_response = httpx.post(
    "http://localhost:8000/workspace/init",
    json={"user_id": "user123"}
)

workspace_path = init_response.json()["local_path"]

# 2. Create session with workspace as cwd
session_response = httpx.post(
    "http://localhost:8000/sessions",
    json={
        "model": "claude-3-5-sonnet-20241022",
        "cwd": workspace_path
    }
)
```

## Error Handling

### Common Errors

**1. S3 Bucket Not Configured**
```json
{
  "detail": "S3_WORKSPACE_BUCKET environment variable not configured"
}
```
**Solution**: Set `S3_WORKSPACE_BUCKET` in `.env` file

**2. s5cmd Not Installed**
```json
{
  "detail": "s5cmd is not installed. Please install it: https://github.com/peak/s5cmd#installation"
}
```
**Solution**: Install s5cmd (see Prerequisites section)

**3. AWS Credentials Not Found**
```json
{
  "detail": "s5cmd failed with exit code 1: ERROR \"NoCredentialProviders: no valid providers in chain\""
}
```
**Solution**: Configure AWS credentials (see Configuration section)

**4. S3 Bucket Access Denied**
```json
{
  "detail": "s5cmd failed with exit code 1: ERROR \"AccessDenied: Access Denied\""
}
```
**Solution**: Check IAM permissions for S3 bucket

**5. Local Workspace Not Found (sync-to-s3)**
```json
{
  "detail": "Local workspace does not exist: /workspace/user123"
}
```
**Solution**: Ensure workspace exists locally before syncing to S3

## Performance

### s5cmd Advantages

s5cmd provides significant performance benefits:
- **Parallel transfers**: Multiple files transferred concurrently
- **Fast**: 10-100x faster than AWS CLI for large transfers
- **Efficient**: Low memory footprint
- **Retry logic**: Automatic retry on transient failures

### Benchmarks

| Tool | 1000 files (100MB) | 10000 files (1GB) |
|------|-------------------|-------------------|
| aws s3 sync | ~45s | ~480s |
| s5cmd sync | ~5s | ~48s |

### Optimization Tips

1. **Use dry_run first**: Verify what will be transferred
2. **Exclude unnecessary files**: Create `.s3ignore` (future feature)
3. **Compress before upload**: For text files, consider compression
4. **Monitor workspace size**: Use `/workspace/info` endpoint

## Security Considerations

1. **IAM Permissions**: Use least-privilege IAM roles
2. **Bucket Policies**: Restrict access to specific user prefixes
3. **Encryption**: Enable S3 bucket encryption at rest
4. **HTTPS**: All S3 transfers use HTTPS by default
5. **User Isolation**: Each user has separate S3 prefix

### Example S3 Bucket Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT_ID:role/AgentServerRole"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-workspace-bucket",
        "arn:aws:s3:::my-workspace-bucket/user_data/*"
      ],
      "Condition": {
        "StringLike": {
          "s3:prefix": ["user_data/${aws:userid}/*"]
        }
      }
    }
  ]
}
```

## Monitoring and Logging

### Log Output

The server logs workspace sync operations:

```
INFO: Initializing workspace for user: user123
INFO: Syncing workspace from s3://bucket/user_data/user123/workspace/* to /workspace/user123
INFO: Workspace sync completed: Successfully synced 42 files from S3
```

### Metrics to Monitor

- Sync duration (latency)
- Files transferred per sync
- Bytes transferred per sync
- Sync failures and errors
- Workspace sizes over time

## Troubleshooting

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger("backend.core.workspace_sync").setLevel(logging.DEBUG)
```

### Test s5cmd Directly

```bash
# Test s5cmd manually
s5cmd --log debug sync \
  's3://my-bucket/user_data/user123/workspace/*' \
  '/workspace/user123/'
```

### Check AWS Credentials

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://my-workspace-bucket/user_data/
```

### Common Issues

**Slow Sync Performance**:
- Check network bandwidth
- Verify s5cmd version (use latest)
- Consider region proximity (S3 bucket and server in same region)

**Partial Transfers**:
- Check disk space on local filesystem
- Review s5cmd output for errors
- Verify S3 bucket has sufficient capacity

## Future Enhancements

Potential improvements:
- Incremental sync (only changed files)
- Compression support
- .s3ignore file support
- Webhook notifications on sync completion
- Scheduled automatic backups
- Multi-region replication
- Version control integration

## References

- [s5cmd Documentation](https://github.com/peak/s5cmd)
- [AWS S3 Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/best-practices.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
