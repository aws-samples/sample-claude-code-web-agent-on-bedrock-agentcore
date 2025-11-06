# Claude Directory Synchronization

This document describes the automatic synchronization and backup of user `.claude` directories to S3.

## Overview

The `.claude` directory contains important Claude Agent SDK data including:
- Session history files (`.jsonl` format)
- User preferences and settings
- Project-specific configurations

The server automatically manages this data with two key features:
1. **Initial Sync**: Downloads user's `.claude` data from S3 on first connection
2. **Periodic Backup**: Continuously backs up `.claude` data to S3

## Configuration

### Environment Variables

```bash
# S3 bucket name (required)
S3_WORKSPACE_BUCKET=my-workspace-bucket

# S3 key prefix (default: "user_data")
S3_WORKSPACE_PREFIX=user_data

# Backup interval in minutes (default: 5)
CLAUDE_BACKUP_INTERVAL_MINUTES=5
```

### S3 Directory Structure

```
s3://bucket-name/
└── user_data/
    └── {user_id}/
        └── .claude/
            ├── projects/
            │   └── {project-key}/
            │       ├── {session-id-1}.jsonl
            │       ├── {session-id-2}.jsonl
            │       └── ...
            └── config/
```

## How It Works

### 1. Initial Sync (First Connection)

When a user first connects to the server:

1. Server receives request with user ID (from JWT token)
2. Checks if this user has been synced in current server session
3. If not synced:
   - Checks if `.claude` data exists in S3
   - **If S3 has data**: Downloads it to local `~/.claude`
   - **If S3 is empty**: Checks for local `~/.claude` data
     - If local data exists: Backs it up to S3 (initial backup)
     - If no local data: Skips (user starts fresh)
   - Marks user as synced to prevent duplicate syncs
4. If already synced: Skips

**Trigger**: Any request to `/invocations` endpoint

**Behavior**:
- Idempotent: Only syncs once per user per server lifetime
- Bi-directional: Downloads from S3 OR uploads to S3 on first connection
- Non-blocking: Sync errors don't fail the request
- Fast: Uses s5cmd for high-performance parallel transfers

**Use Cases**:
- **New user with S3 data**: Restores session history from S3
- **New user without S3 data**: Backs up any existing local sessions to S3
- **Existing user**: Already synced, no action needed

### 2. Periodic Backup

Background task that runs continuously:

1. Waits for configured interval (default: 5 minutes)
2. Gets list of all users who have connected
3. For each user:
   - Checks if `~/.claude` directory exists
   - If exists: Syncs to S3 using s5cmd
   - If not exists: Skips backup
4. Repeats

**Lifecycle**:
- Starts: When server starts
- Stops: When server shuts down

## Features

### Automatic State Management

- **No Database Required**: Sync state maintained in memory
- **Per-Session Tracking**: Each server instance tracks its own sync state
- **Graceful Handling**: Missing S3 data or sync errors don't break functionality

### High Performance

- **s5cmd**: Uses s5cmd for 10-100x faster transfers than AWS CLI
- **Parallel Transfers**: Multiple files transferred concurrently
- **Efficient Sync**: Only transfers changed files

### Error Resilience

- **Non-Fatal Errors**: Sync/backup errors logged but don't fail requests
- **Retry Logic**: Failed initial syncs can be retried on next connection
- **Continuous Operation**: Backup loop continues even if individual backups fail

## Monitoring

### Server Logs

```
# Startup
INFO: Initializing Claude Sync Manager: bucket=my-bucket, prefix=user_data, interval=5m
INFO: Starting .claude backup loop (interval: 5 minutes)
INFO: Background backup task started

# Initial Sync - Download from S3
INFO: Checking if .claude data exists in S3: s3://bucket/user_data/user123/.claude/
INFO: Syncing .claude from s3://bucket/user_data/user123/.claude/ to /root/.claude
INFO: .claude sync completed: Successfully synced 15 files from S3

# Initial Sync - Upload to S3 (no S3 data, but has local data)
INFO: Checking if .claude data exists in S3: s3://bucket/user_data/user456/.claude/
INFO: No .claude data found in S3 for user user456, checking for local .claude data to backup
INFO: Backing up .claude from /root/.claude to s3://bucket/user_data/user456/.claude/
INFO: .claude backup completed: Successfully backed up 8 files to S3
INFO: Initial backup completed for user user456: 8 files backed up to S3

# Periodic Backup
INFO: Starting periodic backup for 3 users
INFO: Backing up .claude from /root/.claude to s3://bucket/user_data/user123/.claude/
INFO: .claude backup completed: Successfully backed up 15 files to S3
INFO: Periodic backup completed

# Shutdown
INFO: Stopping background backup task...
INFO: Background backup task stopped
```

### Sync Manager Stats

Get statistics about the sync manager:

```python
from backend.server import claude_sync_manager

if claude_sync_manager:
    stats = claude_sync_manager.get_stats()
    # Returns:
    # {
    #     "synced_user_count": 10,
    #     "backup_running": True,
    #     "backup_interval_minutes": 5,
    #     "bucket_name": "my-workspace-bucket",
    #     "s3_prefix": "user_data"
    # }
```

## Troubleshooting

### Issue: Initial sync not happening

**Check**:
1. S3_WORKSPACE_BUCKET environment variable is set
2. s5cmd is installed: `which s5cmd`
3. AWS credentials are configured
4. S3 bucket and path exist: `s5cmd ls s3://bucket/user_data/`

**Logs to check**:
```
S3_WORKSPACE_BUCKET not configured, .claude sync/backup will be disabled
```

### Issue: Backup not running

**Check**:
1. Background task started: Look for "Background backup task started" in logs
2. Users have connected: Backup only runs for users who have connected
3. `.claude` directory exists: `ls -la ~/.claude`

**Logs to check**:
```
Starting .claude backup loop (interval: 5 minutes)
No users to backup
```

### Issue: S5cmd errors

**Common errors**:
- **Permission denied**: Check AWS credentials and S3 bucket permissions
- **Bucket not found**: Verify S3_WORKSPACE_BUCKET is correct
- **Command not found**: Install s5cmd

**Fix**:
```bash
# Install s5cmd
# macOS
brew install peak/tap/s5cmd

# Linux
curl -L https://github.com/peak/s5cmd/releases/latest/download/s5cmd_Linux-64bit.tar.gz | tar xz
sudo mv s5cmd /usr/local/bin/

# Verify installation
s5cmd version
```

## Best Practices

### 1. Configure Appropriate Backup Interval

- **Frequent backups (1-5 min)**: For active development, ensures minimal data loss
- **Less frequent backups (10-30 min)**: For production, reduces S3 API calls and costs

### 2. Monitor S3 Costs

- Each backup incurs S3 PUT requests and storage costs
- Use S3 lifecycle policies to archive old session data
- Consider using S3 Intelligent-Tiering for cost optimization

### 3. Handle Multiple Server Instances

- Each server instance manages its own sync state
- Users switching between servers will trigger initial sync on each
- This is intentional and ensures data consistency

### 4. Disaster Recovery

The `.claude` directory in S3 serves as:
- **Backup**: Restore user data after server failure
- **Migration**: Move user data between environments
- **Audit**: Historical record of user sessions

## Implementation Details

### Code Structure

```
backend/
├── core/
│   ├── workspace_sync.py          # S3 sync utilities
│   └── claude_sync_manager.py     # Sync manager class
├── api/
│   └── invocations.py             # Initial sync trigger
└── server.py                       # Lifecycle management
```

### Key Classes

#### `ClaudeSyncManager`
- Tracks synced users
- Manages periodic backup task
- Provides sync/backup methods

#### Main Methods

```python
# Initial sync (idempotent)
await claude_sync_manager.ensure_initial_sync(user_id)

# Manual backup
await claude_sync_manager.backup_user_claude_dir(user_id)

# Get statistics
stats = claude_sync_manager.get_stats()
```

### Sync Functions

```python
# From workspace_sync.py

# Check if S3 directory exists
exists = await check_s3_directory_exists(bucket, prefix)

# Sync from S3 to local
result = await sync_claude_dir_from_s3(user_id, bucket)

# Backup from local to S3
result = await backup_claude_dir_to_s3(user_id, bucket)
```

## Future Enhancements

Potential improvements:
1. **Persistent State**: Store sync state in database or file
2. **Selective Backup**: Only backup changed files
3. **Compression**: Compress session data before upload
4. **Encryption**: Encrypt sensitive session data at rest
5. **Multi-region**: Replicate to multiple S3 regions
6. **Metrics**: Export sync/backup metrics to monitoring system
