"""
Cross-platform path handling.

Provides portable path operations that work correctly on both Windows and Unix.
"""

import os
import pathlib
import tempfile
from typing import Union

from . import IS_WINDOWS


PathLike = Union[str, os.PathLike[str]]


def normalize(path: PathLike) -> str:
    """
    Normalize a path for the current platform.
    
    Converts forward/backslashes appropriately and resolves . and ..
    """
    return os.path.normpath(str(path))


def to_posix(path: PathLike) -> str:
    """Convert a path to POSIX format (forward slashes)."""
    return str(path).replace("\\", "/")


def to_native(path: PathLike) -> str:
    """Convert a path to native format for current OS."""
    if IS_WINDOWS:
        return str(path).replace("/", "\\")
    return str(path).replace("\\", "/")


def join(*parts: PathLike) -> str:
    """Join path components using the appropriate separator."""
    return os.path.join(*[str(p) for p in parts])


def safe_join(base: PathLike, *parts: PathLike) -> str:
    """
    Safely join paths, preventing path traversal attacks.
    
    Raises ValueError if the result would escape the base directory.
    """
    base_resolved = os.path.abspath(str(base))
    result = os.path.abspath(os.path.join(base_resolved, *[str(p) for p in parts]))
    
    # Ensure result is under base
    if not result.startswith(base_resolved + os.sep) and result != base_resolved:
        raise ValueError(f"Path traversal detected: {result} escapes {base_resolved}")
    
    return result


def get_temp_dir() -> str:
    """Get the system temporary directory."""
    return tempfile.gettempdir()


def make_temp_dir(prefix: str = "sansible_") -> str:
    """Create a temporary directory and return its path."""
    return tempfile.mkdtemp(prefix=prefix)


def expand_user(path: PathLike) -> str:
    """Expand ~ to user home directory."""
    return os.path.expanduser(str(path))


def expand_vars(path: PathLike) -> str:
    """Expand environment variables in path."""
    return os.path.expandvars(str(path))


def expand(path: PathLike) -> str:
    """Expand both ~ and environment variables."""
    return expand_vars(expand_user(path))


def get_home_dir() -> str:
    """Get current user's home directory."""
    return os.path.expanduser("~")


def splitext(path: PathLike) -> tuple[str, str]:
    """Split path into (root, extension)."""
    return os.path.splitext(str(path))


def basename(path: PathLike) -> str:
    """Get the final component of a path."""
    return os.path.basename(str(path))


def dirname(path: PathLike) -> str:
    """Get the directory component of a path."""
    return os.path.dirname(str(path))


def exists(path: PathLike) -> bool:
    """Check if a path exists."""
    return os.path.exists(str(path))


def is_file(path: PathLike) -> bool:
    """Check if path is a file."""
    return os.path.isfile(str(path))


def is_dir(path: PathLike) -> bool:
    """Check if path is a directory."""
    return os.path.isdir(str(path))


def is_absolute(path: PathLike) -> bool:
    """Check if path is absolute."""
    return os.path.isabs(str(path))


def abspath(path: PathLike) -> str:
    """Get absolute path."""
    return os.path.abspath(str(path))


def realpath(path: PathLike) -> str:
    """Get real path, resolving symlinks."""
    return os.path.realpath(str(path))
