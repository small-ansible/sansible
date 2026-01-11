# Copyright (c) 2024 Sansible Contributors
# MIT License

"""
Sansible Error Classes.

All custom exceptions for clear error handling and exit codes.
Follows Ansible's error pattern with exit codes matching ansible-playbook behavior.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class ExitCode(enum.IntEnum):
    """Standard exit codes matching ansible-playbook behavior."""

    SUCCESS = 0
    GENERIC_ERROR = 1
    HOST_FAILED = 2
    PARSE_ERROR = 3
    UNSUPPORTED_FEATURE = 4
    KEYBOARD_INTERRUPT = 130


class SansibleError(Exception):
    """Base exception for all Sansible errors."""

    exit_code: int = ExitCode.GENERIC_ERROR

    def __init__(self, message: str, details: str | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message}\n  Details: {self.details}"
        return self.message


class ParseError(SansibleError):
    """Error parsing inventory, playbook, or other input files."""

    exit_code: int = ExitCode.PARSE_ERROR

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        line: int | None = None,
        details: str | None = None,
    ) -> None:
        self.file_path = file_path
        self.line = line
        location = ""
        if file_path:
            location = f" in {file_path}"
            if line:
                location += f" at line {line}"
        super().__init__(f"Parse error{location}: {message}", details)


class UnsupportedFeatureError(SansibleError):
    """Error when playbook uses a feature not supported by Sansible."""

    exit_code: int = ExitCode.UNSUPPORTED_FEATURE

    def __init__(self, feature: str, suggestion: str | None = None) -> None:
        self.feature = feature
        msg = f"Unsupported feature: {feature}"
        if suggestion:
            msg += f"\n  Suggestion: {suggestion}"
        super().__init__(msg)


class ConnectionError(SansibleError):
    """Error connecting to a remote host."""

    exit_code: int = ExitCode.HOST_FAILED

    def __init__(
        self,
        host: str,
        message: str,
        connection_type: str | None = None,
        details: str | None = None,
    ) -> None:
        self.host = host
        self.connection_type = connection_type
        conn_info = f" ({connection_type})" if connection_type else ""
        super().__init__(f"Connection to {host}{conn_info} failed: {message}", details)


class ModuleError(SansibleError):
    """Error executing a module on a host."""

    exit_code: int = ExitCode.HOST_FAILED

    def __init__(
        self,
        module: str,
        host: str,
        message: str,
        rc: int | None = None,
        stdout: str | None = None,
        stderr: str | None = None,
    ) -> None:
        self.module = module
        self.host = host
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr
        
        details_parts = []
        if rc is not None:
            details_parts.append(f"rc={rc}")
        if stderr:
            details_parts.append(f"stderr: {stderr[:200]}")
        
        super().__init__(
            f"Module '{module}' failed on {host}: {message}",
            "; ".join(details_parts) if details_parts else None
        )


class TemplateError(SansibleError):
    """Error rendering a Jinja2 template."""

    exit_code: int = ExitCode.PARSE_ERROR

    def __init__(
        self,
        message: str,
        template: str | None = None,
        variable: str | None = None,
    ) -> None:
        self.template = template
        self.variable = variable
        
        details = None
        if template:
            # Truncate long templates
            truncated = template[:100] + "..." if len(template) > 100 else template
            details = f"Template: {truncated}"
        
        super().__init__(f"Template error: {message}", details)


class HostFailedError(SansibleError):
    """A host has failed during playbook execution."""

    exit_code: int = ExitCode.HOST_FAILED

    def __init__(self, host: str, task: str, message: str) -> None:
        self.host = host
        self.task = task
        super().__init__(f"Host {host} failed at task '{task}': {message}")


class InventoryError(ParseError):
    """Error in inventory file or host resolution."""

    def __init__(self, message: str, file_path: str | None = None) -> None:
        super().__init__(message, file_path=file_path)
