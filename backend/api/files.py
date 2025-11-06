"""
File Browser Endpoints.

Provides REST API endpoints for browsing files and directories.
"""

import os
import mimetypes
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


class FileItem(BaseModel):
    """A file or directory item."""
    name: str
    path: str
    is_directory: bool
    size: Optional[int] = None
    modified: Optional[float] = None


class ListFilesResponse(BaseModel):
    """Response for listing files."""
    path: str
    items: List[FileItem]


class FileInfoResponse(BaseModel):
    """Response for file information."""
    path: str
    name: str
    size: int
    modified: float
    mime_type: Optional[str] = None
    is_text: bool
    content: Optional[str] = None
    error: Optional[str] = None


class SaveFileRequest(BaseModel):
    """Request to save file content."""
    path: str
    content: str


class SaveFileResponse(BaseModel):
    """Response for saving file."""
    success: bool
    path: str
    size: int


router = APIRouter()


@router.get("/files", response_model=ListFilesResponse)
async def list_files(path: str = Query(default=".")):
    """
    List files and directories at the given path.

    Args:
        path: Directory path to list (default: current directory)

    Returns:
        List of files and directories
    """
    try:
        # Resolve the path
        target_path = Path(path).expanduser().resolve()

        # Security check: prevent directory traversal attacks
        # Allow any absolute path or relative path
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")

        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

        # List directory contents
        items = []
        try:
            for entry in sorted(target_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                try:
                    stat = entry.stat()
                    items.append(FileItem(
                        name=entry.name,
                        path=str(entry),
                        is_directory=entry.is_dir(),
                        size=stat.st_size if entry.is_file() else None,
                        modified=stat.st_mtime
                    ))
                except (PermissionError, OSError):
                    # Skip files we can't access
                    continue
        except PermissionError:
            raise HTTPException(status_code=403, detail="Permission denied")

        return ListFilesResponse(
            path=str(target_path),
            items=items
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/files/info", response_model=FileInfoResponse)
async def get_file_info(path: str = Query(...)):
    """
    Get file information and content (if text file).

    Args:
        path: File path to read

    Returns:
        File information and content for text files
    """
    try:
        # Resolve the path
        target_path = Path(path).expanduser().resolve()

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if target_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is a directory, not a file")

        # Get file stats
        stat = target_path.stat()

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(target_path))

        # Check if it's a text file
        is_text = False
        content = None
        error = None

        # Text file detection
        text_mime_types = [
            'text/', 'application/json', 'application/xml',
            'application/javascript', 'application/typescript',
            'application/x-yaml', 'application/x-sh'
        ]

        is_likely_text = (
            mime_type and any(mime_type.startswith(t) for t in text_mime_types)
        ) or target_path.suffix in [
            '.txt', '.md', '.py', '.js', '.jsx', '.ts', '.tsx',
            '.json', '.xml', '.yaml', '.yml', '.sh', '.bash',
            '.css', '.html', '.htm', '.svg', '.log', '.conf',
            '.cfg', '.ini', '.toml', '.rs', '.go', '.java',
            '.c', '.cpp', '.h', '.hpp', '.vue', '.env'
        ]

        if is_likely_text:
            is_text = True
            # Try to read as text
            try:
                # Limit file size to 1MB for preview
                if stat.st_size > 1024 * 1024:
                    error = "File too large for preview (>1MB)"
                else:
                    with open(target_path, 'r', encoding='utf-8') as f:
                        content = f.read()
            except UnicodeDecodeError:
                error = "Cannot decode file as UTF-8 text"
                is_text = False
            except Exception as e:
                error = f"Error reading file: {str(e)}"
                is_text = False

        return FileInfoResponse(
            path=str(target_path),
            name=target_path.name,
            size=stat.st_size,
            modified=stat.st_mtime,
            mime_type=mime_type,
            is_text=is_text,
            content=content,
            error=error
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


@router.post("/files/save", response_model=SaveFileResponse)
async def save_file(request: SaveFileRequest):
    """
    Save content to a file.

    Args:
        request: File path and content to save

    Returns:
        Save confirmation with file size
    """
    try:
        # Resolve the path
        target_path = Path(request.path).expanduser().resolve()

        # Create parent directories if they don't exist
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content to file
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(request.content)

        # Get updated file stats
        stat = target_path.stat()

        return SaveFileResponse(
            success=True,
            path=str(target_path),
            size=stat.st_size
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
