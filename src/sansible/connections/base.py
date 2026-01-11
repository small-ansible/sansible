"""
Sansible Connection Base Class

Abstract base class for all connection types.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

from sansible.engine.inventory import Host


@dataclass
class RunResult:
    """Result of running a command on a remote host."""
    
    rc: int
    stdout: str
    stderr: str
    
    @property
    def success(self) -> bool:
        return self.rc == 0


class Connection(ABC):
    """
    Abstract base class for connections.
    
    All connection types (SSH, WinRM, local) must implement this interface.
    """
    
    def __init__(self, host: Host):
        self.host = host
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish the connection."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the connection."""
        pass
    
    @abstractmethod
    async def run(
        self,
        command: str,
        shell: bool = True,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
        environment: Optional[dict] = None,
    ) -> RunResult:
        """
        Run a command on the remote host.
        
        Args:
            command: Command to execute
            shell: If True, run through a shell
            timeout: Optional timeout in seconds
            cwd: Working directory
            environment: Environment variables
            
        Returns:
            RunResult with rc, stdout, stderr
        """
        pass
    
    @abstractmethod
    async def put(
        self,
        local_path: Path,
        remote_path: str,
        mode: Optional[str] = None,
    ) -> None:
        """
        Upload a file to the remote host.
        
        Args:
            local_path: Local file path
            remote_path: Remote destination path
            mode: Optional file mode (e.g., '0644')
        """
        pass
    
    @abstractmethod
    async def get(
        self,
        remote_path: str,
        local_path: Path,
    ) -> None:
        """
        Download a file from the remote host.
        
        Args:
            remote_path: Remote file path
            local_path: Local destination path
        """
        pass
    
    @abstractmethod
    async def mkdir(self, remote_path: str, mode: Optional[str] = None) -> None:
        """
        Create a directory on the remote host.
        
        Args:
            remote_path: Directory path to create
            mode: Optional directory mode
        """
        pass
    
    @abstractmethod
    async def stat(self, remote_path: str) -> Optional[dict]:
        """
        Get file/directory information.
        
        Args:
            remote_path: Path to stat
            
        Returns:
            Dict with 'exists', 'isdir', 'size', 'mtime' or None if not found
        """
        pass
    
    @property
    def connection_type(self) -> str:
        """Return the connection type name."""
        return self.__class__.__name__.replace('Connection', '').lower()


def create_connection_factory() -> Callable[[Host], Coroutine[Any, Any, Connection]]:
    """
    Create a connection factory function.
    
    Returns a coroutine that creates the appropriate connection based on host settings.
    """
    async def factory(host: Host) -> Connection:
        conn_type = host.ansible_connection
        
        if conn_type == 'local':
            from sansible.connections.local import LocalConnection
            conn = LocalConnection(host)
            await conn.connect()
            return conn
        
        elif conn_type == 'ssh':
            try:
                from sansible.connections.ssh_asyncssh import SSHConnection
                conn = SSHConnection(host)
                await conn.connect()
                return conn
            except ImportError:
                raise ImportError(
                    "SSH support requires asyncssh. "
                    "Install with: pip install sansible[ssh]"
                )
        
        elif conn_type in ('winrm', 'psrp'):
            try:
                from sansible.connections.winrm_psrp import WinRMConnection
                conn = WinRMConnection(host)
                await conn.connect()
                return conn
            except ImportError:
                raise ImportError(
                    "WinRM support requires pypsrp. "
                    "Install with: pip install sansible[winrm]"
                )
        
        else:
            raise ValueError(f"Unknown connection type: {conn_type}")
    
    return factory
