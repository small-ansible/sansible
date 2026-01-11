"""
Sansible SSH Connection (asyncssh)

SSH connection using asyncssh for async operations.
"""

import asyncio
import hashlib
import os
from pathlib import Path
from typing import Optional

from sansible.connections.base import Connection, RunResult
from sansible.engine.inventory import Host

try:
    import asyncssh
    HAS_ASYNCSSH = True
except ImportError:
    HAS_ASYNCSSH = False
    asyncssh = None


class SSHConnection(Connection):
    """
    SSH connection using asyncssh.
    
    Supports:
    - Key-based authentication
    - Password authentication
    - SSH agent
    - Custom ports
    """
    
    def __init__(self, host: Host):
        super().__init__(host)
        
        if not HAS_ASYNCSSH:
            raise ImportError(
                "asyncssh is required for SSH connections. "
                "Install with: pip install sansible[ssh]"
            )
        
        self._conn: Optional[asyncssh.SSHClientConnection] = None
        self._sftp: Optional[asyncssh.SFTPClient] = None
    
    async def connect(self) -> None:
        """Establish SSH connection."""
        host = self.host.ansible_host
        port = self.host.ansible_port
        user = self.host.ansible_user or os.getenv('USER', 'root')
        
        # Get connection parameters from host vars
        password = self.host.get_variable('ansible_password') or \
                   self.host.get_variable('ansible_ssh_pass')
        
        private_key = self.host.get_variable('ansible_ssh_private_key_file')
        
        # Known hosts handling
        known_hosts_policy = self.host.get_variable('ansible_ssh_host_key_checking', True)
        
        connect_kwargs = {
            'host': host,
            'port': port,
            'username': user,
        }
        
        # Add authentication options
        if private_key:
            connect_kwargs['client_keys'] = [private_key]
        
        if password:
            connect_kwargs['password'] = password
        
        # Handle host key checking
        if not known_hosts_policy or str(known_hosts_policy).lower() in ('false', 'no'):
            connect_kwargs['known_hosts'] = None
        
        # Connection timeout
        timeout = self.host.get_variable('ansible_ssh_timeout', 30)
        connect_kwargs['connect_timeout'] = int(timeout)
        
        try:
            self._conn = await asyncssh.connect(**connect_kwargs)
        except Exception as e:
            from sansible.engine.errors import ConnectionError
            raise ConnectionError(
                host=self.host.name,
                message=str(e),
                connection_type='ssh'
            )
    
    async def close(self) -> None:
        """Close SSH connection."""
        if self._sftp:
            self._sftp.exit()
            self._sftp = None
        
        if self._conn:
            self._conn.close()
            await self._conn.wait_closed()
            self._conn = None
    
    async def run(
        self,
        command: str,
        shell: bool = True,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
        environment: Optional[dict] = None,
    ) -> RunResult:
        """
        Run a command over SSH.
        
        Args:
            command: Command to execute
            shell: If True, wrap in shell execution
            timeout: Optional timeout in seconds
            cwd: Working directory (prepends cd command)
            environment: Environment variables
            
        Returns:
            RunResult with rc, stdout, stderr
        """
        if not self._conn:
            return RunResult(rc=1, stdout="", stderr="Not connected")
        
        # Build the command
        full_command = command
        
        if cwd:
            full_command = f"cd {cwd} && {command}"
        
        if shell:
            # Wrap in shell for proper shell behavior
            full_command = f"/bin/sh -c {_shell_quote(full_command)}"
        
        # Add environment variables
        if environment:
            env_prefix = " ".join(f"{k}={_shell_quote(v)}" for k, v in environment.items())
            full_command = f"{env_prefix} {full_command}"
        
        try:
            result = await asyncio.wait_for(
                self._conn.run(full_command, check=False),
                timeout=timeout
            )
            
            return RunResult(
                rc=result.exit_status or 0,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
            )
            
        except asyncio.TimeoutError:
            return RunResult(
                rc=124,
                stdout="",
                stderr="Command timed out",
            )
        except Exception as e:
            return RunResult(
                rc=1,
                stdout="",
                stderr=str(e),
            )
    
    async def _get_sftp(self) -> 'asyncssh.SFTPClient':
        """Get or create SFTP client."""
        if self._sftp is None:
            self._sftp = await self._conn.start_sftp_client()
        return self._sftp
    
    async def put(
        self,
        local_path: Path,
        remote_path: str,
        mode: Optional[str] = None,
    ) -> None:
        """
        Upload a file via SFTP.
        
        Args:
            local_path: Local file path
            remote_path: Remote destination path
            mode: Optional file mode (e.g., '0644')
        """
        sftp = await self._get_sftp()
        
        # Ensure parent directory exists
        remote_dir = str(Path(remote_path).parent)
        try:
            await sftp.makedirs(remote_dir, exist_ok=True)
        except Exception:
            pass  # Directory might already exist
        
        # Upload file
        await sftp.put(str(local_path), remote_path)
        
        # Set permissions if specified
        if mode:
            await sftp.chmod(remote_path, int(mode, 8))
    
    async def get(
        self,
        remote_path: str,
        local_path: Path,
    ) -> None:
        """
        Download a file via SFTP.
        
        Args:
            remote_path: Remote file path
            local_path: Local destination path
        """
        sftp = await self._get_sftp()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        await sftp.get(remote_path, str(local_path))
    
    async def mkdir(self, remote_path: str, mode: Optional[str] = None) -> None:
        """
        Create a directory via SFTP.
        
        Args:
            remote_path: Directory path to create
            mode: Optional directory mode
        """
        sftp = await self._get_sftp()
        await sftp.makedirs(remote_path, exist_ok=True)
        
        if mode:
            await sftp.chmod(remote_path, int(mode, 8))
    
    async def stat(self, remote_path: str) -> Optional[dict]:
        """
        Get file/directory information via SFTP.
        
        Args:
            remote_path: Path to stat
            
        Returns:
            Dict with file info or None if not found
        """
        sftp = await self._get_sftp()
        
        try:
            attrs = await sftp.stat(remote_path)
            
            import stat as stat_module
            
            return {
                'exists': True,
                'isdir': stat_module.S_ISDIR(attrs.permissions or 0),
                'isfile': stat_module.S_ISREG(attrs.permissions or 0),
                'islink': stat_module.S_ISLNK(attrs.permissions or 0),
                'size': attrs.size or 0,
                'mtime': attrs.mtime or 0,
                'mode': oct(attrs.permissions or 0)[-4:],
                'uid': attrs.uid or 0,
                'gid': attrs.gid or 0,
            }
        except (asyncssh.SFTPNoSuchFile, asyncssh.SFTPError):
            return None


def _shell_quote(s: str) -> str:
    """Quote a string for shell use."""
    # Simple single-quote escaping
    return "'" + s.replace("'", "'\"'\"'") + "'"
