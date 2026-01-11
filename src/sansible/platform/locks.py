"""
Cross-platform file locking.

Provides portable file locking that works on both Windows and Unix
using only pure Python (no compiled extensions).
"""

import os
import time
from typing import Optional
from contextlib import contextmanager

from . import IS_WINDOWS


class LockError(Exception):
    """Exception raised when a lock cannot be acquired."""
    pass


class FileLock:
    """
    A cross-platform file lock implementation.
    
    Uses fcntl on Unix and msvcrt on Windows, both of which are
    standard library modules (pure Python interface to OS primitives).
    """
    
    def __init__(self, path: str, timeout: Optional[float] = None):
        """
        Initialize a file lock.
        
        Args:
            path: Path to the lock file
            timeout: Maximum time to wait for lock (None = forever)
        """
        self.path = path
        self.timeout = timeout
        self._lock_file = None
        self._locked = False
    
    def acquire(self, blocking: bool = True) -> bool:
        """
        Acquire the lock.
        
        Args:
            blocking: If True, wait for lock. If False, return immediately.
        
        Returns:
            True if lock acquired, False if non-blocking and lock unavailable.
        
        Raises:
            LockError: If blocking with timeout and timeout exceeded.
        """
        # Create lock file directory if needed
        lock_dir = os.path.dirname(self.path)
        if lock_dir and not os.path.exists(lock_dir):
            os.makedirs(lock_dir, exist_ok=True)
        
        # Open lock file
        self._lock_file = open(self.path, "w")
        
        start_time = time.monotonic()
        
        while True:
            try:
                if IS_WINDOWS:
                    self._lock_windows()
                else:
                    self._lock_unix()
                
                self._locked = True
                return True
                
            except (IOError, OSError):
                if not blocking:
                    self._lock_file.close()
                    self._lock_file = None
                    return False
                
                # Check timeout
                if self.timeout is not None:
                    elapsed = time.monotonic() - start_time
                    if elapsed >= self.timeout:
                        self._lock_file.close()
                        self._lock_file = None
                        raise LockError(f"Timeout waiting for lock: {self.path}")
                
                # Wait a bit before retrying
                time.sleep(0.1)
    
    def release(self) -> None:
        """Release the lock."""
        if not self._locked or self._lock_file is None:
            return
        
        try:
            if IS_WINDOWS:
                self._unlock_windows()
            else:
                self._unlock_unix()
        finally:
            self._locked = False
            self._lock_file.close()
            self._lock_file = None
    
    def _lock_unix(self) -> None:
        """Acquire lock on Unix using fcntl."""
        import fcntl
        fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    
    def _unlock_unix(self) -> None:
        """Release lock on Unix using fcntl."""
        import fcntl
        fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
    
    def _lock_windows(self) -> None:
        """Acquire lock on Windows using msvcrt."""
        import msvcrt
        msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_NBLCK, 1)
    
    def _unlock_windows(self) -> None:
        """Release lock on Windows using msvcrt."""
        import msvcrt
        try:
            self._lock_file.seek(0)
            msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        except Exception:
            pass  # Best effort unlock
    
    @property
    def is_locked(self) -> bool:
        """Check if lock is currently held."""
        return self._locked
    
    def __enter__(self) -> "FileLock":
        self.acquire()
        return self
    
    def __exit__(self, *args) -> None:
        self.release()
    
    def __del__(self) -> None:
        self.release()


@contextmanager
def file_lock(path: str, timeout: Optional[float] = None):
    """
    Context manager for file locking.
    
    Usage:
        with file_lock("/tmp/myapp.lock"):
            # Critical section
            pass
    """
    lock = FileLock(path, timeout)
    lock.acquire()
    try:
        yield lock
    finally:
        lock.release()


class SimpleLock:
    """
    A simple in-memory lock for thread synchronization.
    
    This is just a wrapper around threading.Lock for API consistency.
    """
    
    def __init__(self):
        import threading
        self._lock = threading.Lock()
    
    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
        return self._lock.acquire(blocking, timeout)
    
    def release(self) -> None:
        self._lock.release()
    
    def __enter__(self) -> "SimpleLock":
        self.acquire()
        return self
    
    def __exit__(self, *args) -> None:
        self.release()
