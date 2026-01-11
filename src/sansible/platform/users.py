"""
Cross-platform user and permission handling.

Provides portable user/permission operations that work on both Windows and Unix.
On Windows, many Unix-specific concepts (uid, gid) are stubbed or adapted.
"""

import os
from typing import Optional, Tuple

from . import IS_WINDOWS


def get_current_user() -> str:
    """Get the current username."""
    if IS_WINDOWS:
        return os.environ.get("USERNAME", os.environ.get("USER", "unknown"))
    else:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_name


def get_uid() -> int:
    """
    Get current user ID.
    
    On Windows, returns a placeholder value (always 1000).
    """
    if IS_WINDOWS:
        return 1000  # Placeholder for Windows
    else:
        return os.getuid()


def get_gid() -> int:
    """
    Get current group ID.
    
    On Windows, returns a placeholder value (always 1000).
    """
    if IS_WINDOWS:
        return 1000  # Placeholder for Windows
    else:
        return os.getgid()


def get_uid_gid() -> Tuple[int, int]:
    """Get both uid and gid as a tuple."""
    return (get_uid(), get_gid())


def get_home_dir() -> str:
    """Get the current user's home directory."""
    return os.path.expanduser("~")


def user_exists(username: str) -> bool:
    """
    Check if a user exists on the system.
    
    On Windows, this checks environment variables only (limited).
    """
    if IS_WINDOWS:
        current = os.environ.get("USERNAME", os.environ.get("USER", ""))
        return username.lower() == current.lower()
    else:
        import pwd
        try:
            pwd.getpwnam(username)
            return True
        except KeyError:
            return False


def get_user_home(username: str) -> Optional[str]:
    """
    Get the home directory for a specific user.
    
    Returns None if user not found.
    On Windows, only works for current user.
    """
    if IS_WINDOWS:
        current = os.environ.get("USERNAME", os.environ.get("USER", ""))
        if username.lower() == current.lower():
            return get_home_dir()
        return None
    else:
        import pwd
        try:
            return pwd.getpwnam(username).pw_dir
        except KeyError:
            return None


def is_root() -> bool:
    """
    Check if running as root/administrator.
    
    On Windows, checks for admin rights.
    """
    if IS_WINDOWS:
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.getuid() == 0


def can_become_user(username: str) -> bool:
    """
    Check if we can become (sudo to) another user.
    
    On Windows, always returns False (use RunAs instead).
    """
    if IS_WINDOWS:
        return False
    else:
        # On Unix, check if we're root or if sudo is available
        if is_root():
            return True
        
        # Check if sudo is available and configured
        # This is a simplified check
        import shutil
        return shutil.which("sudo") is not None


class UserContext:
    """
    Context manager for temporarily switching user context.
    
    On Windows, this is a no-op (Windows doesn't support Unix-style user switching).
    """
    
    def __init__(self, username: Optional[str] = None, uid: Optional[int] = None):
        self.target_username = username
        self.target_uid = uid
        self._original_uid: Optional[int] = None
        self._original_gid: Optional[int] = None
    
    def __enter__(self) -> "UserContext":
        if IS_WINDOWS:
            return self  # No-op on Windows
        
        self._original_uid = os.getuid()
        self._original_gid = os.getgid()
        
        # Note: Actually switching users requires root privileges
        # This is mainly a placeholder for the interface
        
        return self
    
    def __exit__(self, *args) -> None:
        if IS_WINDOWS:
            return  # No-op on Windows
        
        # Restore original context if changed
        # (In practice, this requires careful handling)
        pass
