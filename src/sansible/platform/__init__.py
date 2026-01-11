"""
Platform abstraction layer for cross-platform compatibility.

This package provides portable implementations of OS-specific functionality,
ensuring sansible works identically on Windows and Unix systems.
"""

import platform as _platform

# Detect current platform
IS_WINDOWS = _platform.system() == "Windows"
IS_LINUX = _platform.system() == "Linux"
IS_MACOS = _platform.system() == "Darwin"
IS_POSIX = not IS_WINDOWS

PLATFORM_NAME = _platform.system().lower()
