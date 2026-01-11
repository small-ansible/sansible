"""
Cross-platform TTY and terminal handling.

Provides portable terminal/console operations that work on both Windows and Unix.
"""

import os
import sys
from typing import Optional, TextIO

from . import IS_WINDOWS


def is_tty(stream: Optional[TextIO] = None) -> bool:
    """
    Check if the given stream (or stdout) is a TTY.
    
    This works correctly on both Windows and Unix.
    """
    if stream is None:
        stream = sys.stdout
    
    try:
        return stream.isatty()
    except AttributeError:
        return False


def supports_color(stream: Optional[TextIO] = None) -> bool:
    """
    Check if the stream supports ANSI color codes.
    
    On Windows, this checks for Windows Terminal, ConEmu, or
    other terminals that support ANSI escape sequences.
    """
    if stream is None:
        stream = sys.stdout
    
    # If not a TTY, no color support
    if not is_tty(stream):
        return False
    
    # Check for explicit disable
    if os.environ.get("NO_COLOR"):
        return False
    
    # Check for explicit enable
    if os.environ.get("FORCE_COLOR"):
        return True
    
    if IS_WINDOWS:
        return _windows_supports_color()
    else:
        # Most Unix terminals support color
        term = os.environ.get("TERM", "")
        return term != "dumb"


def _windows_supports_color() -> bool:
    """Check if Windows console supports ANSI colors."""
    # Windows Terminal always supports ANSI
    if os.environ.get("WT_SESSION"):
        return True
    
    # ConEmu supports ANSI
    if os.environ.get("ConEmuANSI") == "ON":
        return True
    
    # VSCode terminal supports ANSI
    if os.environ.get("TERM_PROGRAM") == "vscode":
        return True
    
    # Windows 10 1511+ supports ANSI in cmd.exe with VirtualTerminalLevel
    # Try to enable it
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        
        # STD_OUTPUT_HANDLE = -11
        handle = kernel32.GetStdHandle(-11)
        
        # Get current mode
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        # Try to enable it
        new_mode = mode.value | 0x0004
        if kernel32.SetConsoleMode(handle, new_mode):
            return True
    except Exception:
        pass
    
    return False


def get_terminal_size() -> tuple[int, int]:
    """
    Get terminal size as (columns, lines).
    
    Returns (80, 24) as default if size cannot be determined.
    """
    try:
        size = os.get_terminal_size()
        return (size.columns, size.lines)
    except OSError:
        return (80, 24)


# ANSI color codes
class Colors:
    """ANSI color codes for terminal output."""
    
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


class ColorPrinter:
    """Helper class for printing colored output."""
    
    def __init__(self, stream: Optional[TextIO] = None):
        self.stream = stream or sys.stdout
        self.enabled = supports_color(self.stream)
    
    def _wrap(self, text: str, *codes: str) -> str:
        """Wrap text with color codes if enabled."""
        if not self.enabled:
            return text
        return "".join(codes) + text + Colors.RESET
    
    def red(self, text: str) -> str:
        return self._wrap(text, Colors.RED)
    
    def green(self, text: str) -> str:
        return self._wrap(text, Colors.GREEN)
    
    def yellow(self, text: str) -> str:
        return self._wrap(text, Colors.YELLOW)
    
    def blue(self, text: str) -> str:
        return self._wrap(text, Colors.BLUE)
    
    def cyan(self, text: str) -> str:
        return self._wrap(text, Colors.CYAN)
    
    def bold(self, text: str) -> str:
        return self._wrap(text, Colors.BOLD)
    
    def dim(self, text: str) -> str:
        return self._wrap(text, Colors.DIM)
    
    def success(self, text: str) -> str:
        return self._wrap(text, Colors.BRIGHT_GREEN, Colors.BOLD)
    
    def error(self, text: str) -> str:
        return self._wrap(text, Colors.BRIGHT_RED, Colors.BOLD)
    
    def warning(self, text: str) -> str:
        return self._wrap(text, Colors.BRIGHT_YELLOW)
    
    def info(self, text: str) -> str:
        return self._wrap(text, Colors.BRIGHT_CYAN)


# Default color printer for stdout
printer = ColorPrinter()
