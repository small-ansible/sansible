"""
Cross-platform process execution.

Provides portable subprocess operations that work correctly on both Windows and Unix.
"""

import os
import shlex
import subprocess
import sys
from typing import Optional, Union, Sequence, Mapping

from . import IS_WINDOWS


# Type aliases
CommandArg = Union[str, bytes, "os.PathLike[str]", "os.PathLike[bytes]"]
CommandSequence = Sequence[CommandArg]


class ProcessResult:
    """Result of a process execution."""
    
    def __init__(
        self,
        returncode: int,
        stdout: str,
        stderr: str,
        command: Union[str, CommandSequence],
    ):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.command = command
    
    @property
    def success(self) -> bool:
        """Check if process exited successfully."""
        return self.returncode == 0
    
    @property
    def failed(self) -> bool:
        """Check if process failed."""
        return self.returncode != 0
    
    def __repr__(self) -> str:
        return f"ProcessResult(returncode={self.returncode}, stdout={len(self.stdout)} chars)"


def quote_arg(arg: str) -> str:
    """
    Quote a single argument for shell use.
    
    Uses appropriate quoting for the current platform.
    """
    if IS_WINDOWS:
        return _quote_windows(arg)
    else:
        return shlex.quote(arg)


def _quote_windows(arg: str) -> str:
    """
    Quote an argument for Windows cmd.exe.
    
    This is more complex than Unix quoting due to cmd.exe quirks.
    """
    if not arg:
        return '""'
    
    # Check if quoting is needed
    if not any(c in arg for c in ' \t\n\r"^&|<>()'):
        return arg
    
    # Escape internal quotes and wrap
    result = []
    num_backslashes = 0
    
    for char in arg:
        if char == '\\':
            num_backslashes += 1
        elif char == '"':
            # Escape backslashes before quote
            result.extend(['\\'] * (num_backslashes * 2 + 1))
            result.append('"')
            num_backslashes = 0
        else:
            result.extend(['\\'] * num_backslashes)
            result.append(char)
            num_backslashes = 0
    
    # Handle trailing backslashes
    result.extend(['\\'] * (num_backslashes * 2))
    
    return '"' + ''.join(result) + '"'


def quote_command(args: Sequence[str]) -> str:
    """Quote a command sequence for shell execution."""
    return " ".join(quote_arg(arg) for arg in args)


def run(
    cmd: Union[str, CommandSequence],
    *,
    cwd: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    timeout: Optional[float] = None,
    check: bool = False,
    capture_output: bool = True,
    input: Optional[str] = None,
    encoding: str = "utf-8",
    shell: bool = False,
) -> ProcessResult:
    """
    Run a command and return the result.
    
    Args:
        cmd: Command to run (string for shell, sequence for direct exec)
        cwd: Working directory
        env: Environment variables (merged with current env)
        timeout: Timeout in seconds
        check: Raise exception on non-zero exit
        capture_output: Capture stdout/stderr
        input: String to send to stdin
        encoding: Output encoding
        shell: Use shell to execute (careful with untrusted input!)
    
    Returns:
        ProcessResult with returncode, stdout, stderr
    
    Raises:
        subprocess.TimeoutExpired: If timeout exceeded
        subprocess.CalledProcessError: If check=True and process fails
    """
    # Prepare environment
    run_env = dict(os.environ)
    if env:
        run_env.update(env)
    
    # Prepare subprocess arguments
    kwargs: dict = {
        "cwd": cwd,
        "env": run_env,
        "timeout": timeout,
        "shell": shell,
    }
    
    if capture_output:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    
    if input is not None:
        kwargs["stdin"] = subprocess.PIPE
        kwargs["input"] = input.encode(encoding)
    
    # Run the command
    try:
        result = subprocess.run(cmd, **kwargs)
    except subprocess.TimeoutExpired:
        raise
    except FileNotFoundError as e:
        # Provide a clearer error message
        cmd_str = cmd if isinstance(cmd, str) else cmd[0]
        raise FileNotFoundError(f"Command not found: {cmd_str}") from e
    
    # Decode output
    stdout = ""
    stderr = ""
    if capture_output:
        stdout = result.stdout.decode(encoding, errors="replace") if result.stdout else ""
        stderr = result.stderr.decode(encoding, errors="replace") if result.stderr else ""
    
    proc_result = ProcessResult(
        returncode=result.returncode,
        stdout=stdout,
        stderr=stderr,
        command=cmd,
    )
    
    if check and proc_result.failed:
        raise subprocess.CalledProcessError(
            result.returncode,
            cmd,
            result.stdout,
            result.stderr,
        )
    
    return proc_result


def run_shell(
    command: str,
    *,
    cwd: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    timeout: Optional[float] = None,
    check: bool = False,
) -> ProcessResult:
    """
    Run a shell command.
    
    This is a convenience wrapper around run() with shell=True.
    Be careful with untrusted input!
    """
    return run(
        command,
        shell=True,
        cwd=cwd,
        env=env,
        timeout=timeout,
        check=check,
    )


def which(program: str) -> Optional[str]:
    """
    Find the full path to an executable.
    
    Returns None if not found.
    """
    import shutil
    return shutil.which(program)


def get_python_executable() -> str:
    """Get the path to the current Python interpreter."""
    return sys.executable


def is_command_available(program: str) -> bool:
    """Check if a command is available on the system."""
    return which(program) is not None


def get_shell() -> list[str]:
    """
    Get the appropriate shell for the current platform.
    
    Returns command prefix for shell execution.
    """
    if IS_WINDOWS:
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        return [comspec, "/c"]
    else:
        shell = os.environ.get("SHELL", "/bin/sh")
        return [shell, "-c"]
