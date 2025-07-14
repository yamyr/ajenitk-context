"""File system tools for reading, writing, and managing files."""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from ..base import Tool, ToolParameter, ToolResult, ToolError, ToolParameterType
from ..decorators import tool


class ReadFileTool(Tool):
    """Tool for reading file contents."""
    
    @property
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return "Read the contents of a file"
    
    @property
    def category(self) -> str:
        return "file_system"
    
    @property
    def is_safe(self) -> bool:
        return True
    
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type=ToolParameterType.FILE_PATH,
                description="Path to the file to read",
                required=True
            ),
            ToolParameter(
                name="encoding",
                type=ToolParameterType.STRING,
                description="File encoding",
                required=False,
                default="utf-8"
            )
        ]
    
    def execute(self, path: str, encoding: str = "utf-8") -> ToolResult:
        try:
            file_path = Path(path).resolve()
            
            # Security check - prevent reading outside working directory
            # This is a simple check, real implementation might need more sophisticated sandboxing
            
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    error=f"File does not exist: {path}"
                )
            
            if not file_path.is_file():
                return ToolResult(
                    success=False,
                    error=f"Path is not a file: {path}"
                )
            
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            return ToolResult(
                success=True,
                data=content,
                metadata={
                    "file_path": str(file_path),
                    "size": file_path.stat().st_size,
                    "encoding": encoding
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"error_type": type(e).__name__}
            )


class WriteFileTool(Tool):
    """Tool for writing content to files."""
    
    @property
    def name(self) -> str:
        return "write_file"
    
    @property
    def description(self) -> str:
        return "Write content to a file"
    
    @property
    def category(self) -> str:
        return "file_system"
    
    @property
    def requires_confirmation(self) -> bool:
        return True
    
    @property
    def is_safe(self) -> bool:
        return False
    
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type=ToolParameterType.FILE_PATH,
                description="Path to the file to write",
                required=True
            ),
            ToolParameter(
                name="content",
                type=ToolParameterType.STRING,
                description="Content to write to the file",
                required=True
            ),
            ToolParameter(
                name="encoding",
                type=ToolParameterType.STRING,
                description="File encoding",
                required=False,
                default="utf-8"
            ),
            ToolParameter(
                name="create_dirs",
                type=ToolParameterType.BOOLEAN,
                description="Create parent directories if they don't exist",
                required=False,
                default=False
            ),
            ToolParameter(
                name="overwrite",
                type=ToolParameterType.BOOLEAN,
                description="Overwrite file if it exists",
                required=False,
                default=False
            )
        ]
    
    def execute(self, path: str, content: str, encoding: str = "utf-8", 
                create_dirs: bool = False, overwrite: bool = False) -> ToolResult:
        try:
            file_path = Path(path).resolve()
            
            # Check if file exists and overwrite is False
            if file_path.exists() and not overwrite:
                return ToolResult(
                    success=False,
                    error=f"File already exists: {path}. Set overwrite=True to overwrite."
                )
            
            # Create parent directories if requested
            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)
            elif not file_path.parent.exists():
                return ToolResult(
                    success=False,
                    error=f"Parent directory does not exist: {file_path.parent}"
                )
            
            # Write the file
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            
            return ToolResult(
                success=True,
                data={"written_bytes": len(content.encode(encoding))},
                metadata={
                    "file_path": str(file_path),
                    "encoding": encoding,
                    "created": not file_path.exists()
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"error_type": type(e).__name__}
            )


class ListDirectoryTool(Tool):
    """Tool for listing directory contents."""
    
    @property
    def name(self) -> str:
        return "list_directory"
    
    @property
    def description(self) -> str:
        return "List contents of a directory"
    
    @property
    def category(self) -> str:
        return "file_system"
    
    @property
    def is_safe(self) -> bool:
        return True
    
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type=ToolParameterType.FILE_PATH,
                description="Path to the directory",
                required=True
            ),
            ToolParameter(
                name="recursive",
                type=ToolParameterType.BOOLEAN,
                description="List subdirectories recursively",
                required=False,
                default=False
            ),
            ToolParameter(
                name="include_hidden",
                type=ToolParameterType.BOOLEAN,
                description="Include hidden files (starting with .)",
                required=False,
                default=False
            ),
            ToolParameter(
                name="pattern",
                type=ToolParameterType.STRING,
                description="Glob pattern to filter files",
                required=False,
                default=None
            )
        ]
    
    def execute(self, path: str, recursive: bool = False, 
                include_hidden: bool = False, pattern: Optional[str] = None) -> ToolResult:
        try:
            dir_path = Path(path).resolve()
            
            if not dir_path.exists():
                return ToolResult(
                    success=False,
                    error=f"Directory does not exist: {path}"
                )
            
            if not dir_path.is_dir():
                return ToolResult(
                    success=False,
                    error=f"Path is not a directory: {path}"
                )
            
            entries = []
            
            if recursive:
                # Use rglob for recursive listing
                if pattern:
                    file_iter = dir_path.rglob(pattern)
                else:
                    file_iter = dir_path.rglob("*")
            else:
                # Use glob for non-recursive listing
                if pattern:
                    file_iter = dir_path.glob(pattern)
                else:
                    file_iter = dir_path.glob("*")
            
            for entry in file_iter:
                # Skip hidden files if not requested
                if not include_hidden and entry.name.startswith('.'):
                    continue
                
                try:
                    stat = entry.stat()
                    entries.append({
                        "name": entry.name,
                        "path": str(entry),
                        "type": "directory" if entry.is_dir() else "file",
                        "size": stat.st_size if entry.is_file() else None,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "permissions": oct(stat.st_mode)[-3:]
                    })
                except Exception as e:
                    # Skip files we can't access
                    continue
            
            return ToolResult(
                success=True,
                data=entries,
                metadata={
                    "directory": str(dir_path),
                    "count": len(entries),
                    "recursive": recursive
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"error_type": type(e).__name__}
            )


# Using the decorator approach for simpler tools

@tool(
    name="delete_file",
    description="Delete a file or empty directory",
    category="file_system",
    requires_confirmation=True,
    is_safe=False
)
def delete_file(path: str, force: bool = False) -> Dict[str, Any]:
    """Delete a file or empty directory.
    
    Args:
        path: Path to delete
        force: Force deletion of non-empty directories
    
    Returns:
        Dictionary with deletion status
    """
    file_path = Path(path).resolve()
    
    if not file_path.exists():
        raise ToolError(f"Path does not exist: {path}")
    
    if file_path.is_dir():
        if force:
            shutil.rmtree(file_path)
        else:
            file_path.rmdir()  # Will fail if not empty
    else:
        file_path.unlink()
    
    return {
        "deleted": str(file_path),
        "type": "directory" if file_path.is_dir() else "file"
    }


@tool(
    name="create_directory",
    description="Create a new directory",
    category="file_system",
    is_safe=False
)
def create_directory(path: str, parents: bool = True, exist_ok: bool = True) -> Dict[str, Any]:
    """Create a new directory.
    
    Args:
        path: Path of directory to create
        parents: Create parent directories if needed
        exist_ok: Don't raise error if directory exists
    
    Returns:
        Dictionary with creation status
    """
    dir_path = Path(path).resolve()
    
    created = not dir_path.exists()
    dir_path.mkdir(parents=parents, exist_ok=exist_ok)
    
    return {
        "path": str(dir_path),
        "created": created,
        "parents_created": parents
    }


@tool(
    name="file_exists",
    description="Check if a file or directory exists",
    category="file_system",
    is_safe=True
)
def file_exists(path: str) -> Dict[str, Any]:
    """Check if a file or directory exists.
    
    Args:
        path: Path to check
    
    Returns:
        Dictionary with existence information
    """
    file_path = Path(path).resolve()
    
    return {
        "exists": file_path.exists(),
        "is_file": file_path.is_file() if file_path.exists() else None,
        "is_directory": file_path.is_dir() if file_path.exists() else None,
        "absolute_path": str(file_path)
    }


@tool(
    name="get_file_info",
    description="Get detailed information about a file or directory",
    category="file_system",
    is_safe=True
)
def get_file_info(path: str) -> Dict[str, Any]:
    """Get detailed information about a file or directory.
    
    Args:
        path: Path to get info for
    
    Returns:
        Dictionary with file information
    """
    file_path = Path(path).resolve()
    
    if not file_path.exists():
        raise ToolError(f"Path does not exist: {path}")
    
    stat = file_path.stat()
    
    info = {
        "name": file_path.name,
        "path": str(file_path),
        "type": "directory" if file_path.is_dir() else "file",
        "size": stat.st_size,
        "size_human": _format_size(stat.st_size),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
        "permissions": oct(stat.st_mode)[-3:],
        "owner_id": stat.st_uid,
        "group_id": stat.st_gid
    }
    
    if file_path.is_file():
        info["extension"] = file_path.suffix
        info["mime_type"] = _guess_mime_type(file_path)
    elif file_path.is_dir():
        try:
            info["item_count"] = len(list(file_path.iterdir()))
        except:
            info["item_count"] = None
    
    return info


def _format_size(size: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def _guess_mime_type(path: Path) -> Optional[str]:
    """Guess MIME type from file extension."""
    import mimetypes
    mime_type, _ = mimetypes.guess_type(str(path))
    return mime_type


# Create tool instances for registration
DeleteFileTool = delete_file.tool
CreateDirectoryTool = create_directory.tool  
FileExistsTool = file_exists.tool
GetFileInfoTool = get_file_info.tool