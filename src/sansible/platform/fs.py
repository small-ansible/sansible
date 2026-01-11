"""
Cross-platform filesystem operations.

Provides portable file operations that work correctly on both Windows and Unix.
"""

import os
import shutil
import stat
import tempfile
from typing import Union, Optional
from contextlib import contextmanager

from . import IS_WINDOWS
from .paths import PathLike


def read_file(path: PathLike, encoding: str = "utf-8") -> str:
    """Read entire file as string."""
    with open(path, "r", encoding=encoding) as f:
        return f.read()


def read_bytes(path: PathLike) -> bytes:
    """Read entire file as bytes."""
    with open(path, "rb") as f:
        return f.read()


def write_file(path: PathLike, content: str, encoding: str = "utf-8") -> None:
    """Write string to file."""
    with open(path, "w", encoding=encoding) as f:
        f.write(content)


def write_bytes(path: PathLike, content: bytes) -> None:
    """Write bytes to file."""
    with open(path, "wb") as f:
        f.write(content)


def atomic_write(
    path: PathLike,
    content: Union[str, bytes],
    encoding: str = "utf-8"
) -> None:
    """
    Atomically write content to a file.
    
    Writes to a temporary file first, then renames to target path.
    This ensures the file is never partially written.
    """
    path_str = str(path)
    dir_path = os.path.dirname(path_str) or "."
    
    # Create temp file in same directory for atomic rename
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, prefix=".tmp_")
    try:
        if isinstance(content, bytes):
            os.write(fd, content)
        else:
            os.write(fd, content.encode(encoding))
        os.close(fd)
        
        # On Windows, we need to remove the target first
        if IS_WINDOWS and os.path.exists(path_str):
            os.remove(path_str)
        
        os.rename(tmp_path, path_str)
    except:
        os.close(fd) if not os.get_inheritable(fd) else None
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def makedirs(path: PathLike, exist_ok: bool = True) -> None:
    """Create directory and all parent directories."""
    os.makedirs(str(path), exist_ok=exist_ok)


def remove(path: PathLike) -> None:
    """Remove a file."""
    os.remove(str(path))


def rmtree(path: PathLike) -> None:
    """Remove a directory tree."""
    shutil.rmtree(str(path))


def copy_file(src: PathLike, dst: PathLike) -> None:
    """Copy a file, preserving metadata where possible."""
    shutil.copy2(str(src), str(dst))


def copy_tree(src: PathLike, dst: PathLike) -> None:
    """Copy a directory tree."""
    shutil.copytree(str(src), str(dst))


def move(src: PathLike, dst: PathLike) -> None:
    """Move a file or directory."""
    shutil.move(str(src), str(dst))


def chmod(path: PathLike, mode: int, follow_symlinks: bool = True) -> bool:
    """
    Set file permissions (best-effort on Windows).
    
    Returns True if successful, False if not applicable (Windows).
    """
    if IS_WINDOWS:
        # Windows doesn't have Unix permissions
        # We can only toggle read-only flag
        try:
            if mode & stat.S_IWRITE:
                os.chmod(str(path), stat.S_IWRITE)
            else:
                os.chmod(str(path), stat.S_IREAD)
            return True
        except OSError:
            return False
    else:
        os.chmod(str(path), mode, follow_symlinks=follow_symlinks)
        return True


def get_mode(path: PathLike) -> int:
    """Get file permission mode."""
    return os.stat(str(path)).st_mode


def is_executable(path: PathLike) -> bool:
    """Check if file is executable."""
    if IS_WINDOWS:
        # On Windows, check extension
        ext = os.path.splitext(str(path))[1].lower()
        return ext in {".exe", ".bat", ".cmd", ".com", ".ps1"}
    else:
        return os.access(str(path), os.X_OK)


def make_executable(path: PathLike) -> bool:
    """Make a file executable (no-op on Windows)."""
    if IS_WINDOWS:
        return True  # Windows uses extensions, not permissions
    
    current = get_mode(path)
    # Add execute permission for owner, group, others (where read is set)
    new_mode = current
    if current & stat.S_IRUSR:
        new_mode |= stat.S_IXUSR
    if current & stat.S_IRGRP:
        new_mode |= stat.S_IXGRP
    if current & stat.S_IROTH:
        new_mode |= stat.S_IXOTH
    
    os.chmod(str(path), new_mode)
    return True


def symlink(src: PathLike, dst: PathLike) -> bool:
    """
    Create a symbolic link (best-effort on Windows).
    
    Returns True if successful, False otherwise.
    Note: Windows symlinks require special permissions.
    """
    try:
        os.symlink(str(src), str(dst))
        return True
    except OSError:
        return False


def is_symlink(path: PathLike) -> bool:
    """Check if path is a symbolic link."""
    return os.path.islink(str(path))


def listdir(path: PathLike) -> list[str]:
    """List directory contents."""
    return os.listdir(str(path))


def walk(path: PathLike):
    """Walk directory tree."""
    return os.walk(str(path))


@contextmanager
def temp_directory(prefix: str = "sansible_"):
    """Context manager that creates and cleans up a temporary directory."""
    tmp_dir = tempfile.mkdtemp(prefix=prefix)
    try:
        yield tmp_dir
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@contextmanager
def temp_file(
    suffix: str = "",
    prefix: str = "sansible_",
    dir: Optional[str] = None,
    delete: bool = True
):
    """Context manager that creates and cleans up a temporary file."""
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
    os.close(fd)
    try:
        yield path
    finally:
        if delete and os.path.exists(path):
            os.remove(path)
