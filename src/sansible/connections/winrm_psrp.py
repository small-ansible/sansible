"""
Sansible WinRM/PSRP Connection

Windows Remote Management connection using pypsrp.
"""

import asyncio
import base64
import os
import tempfile
from pathlib import Path
from typing import Optional

from sansible.connections.base import Connection, RunResult
from sansible.engine.inventory import Host

try:
    from pypsrp.client import Client
    from pypsrp.powershell import PowerShell, RunspacePool
    from pypsrp.wsman import WSMan
    HAS_PYPSRP = True
except ImportError:
    HAS_PYPSRP = False
    Client = None
    PowerShell = None
    RunspacePool = None
    WSMan = None


# Chunk size for file transfers (700KB to stay under WinRM limits)
CHUNK_SIZE = 700 * 1024


class WinRMConnection(Connection):
    """
    WinRM connection using pypsrp (PowerShell Remoting Protocol).
    
    Supports:
    - NTLM authentication
    - Basic authentication
    - Kerberos authentication (if configured)
    - SSL/TLS connections
    """
    
    def __init__(self, host: Host):
        super().__init__(host)
        
        if not HAS_PYPSRP:
            raise ImportError(
                "pypsrp is required for WinRM connections. "
                "Install with: pip install sansible[winrm]"
            )
        
        self._client: Optional[Client] = None
        self._wsman: Optional[WSMan] = None
    
    async def connect(self) -> None:
        """Establish WinRM connection."""
        # Run synchronous pypsrp connection in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_connect)
    
    def _sync_connect(self) -> None:
        """Synchronous connection setup."""
        host = self.host.ansible_host
        port = self.host.get_variable('ansible_port', 5985)
        
        # Get credentials
        user = self.host.ansible_user
        password = self.host.get_variable('ansible_password') or \
                   self.host.get_variable('ansible_winrm_password')
        
        # Connection options
        ssl = self.host.get_variable('ansible_winrm_transport', 'ntlm') == 'ssl'
        if self.host.get_variable('ansible_winrm_scheme', 'http') == 'https':
            ssl = True
            port = self.host.get_variable('ansible_port', 5986)
        
        cert_validation = self.host.get_variable('ansible_winrm_server_cert_validation', True)
        
        # Authentication method
        auth = self.host.get_variable('ansible_winrm_transport', 'ntlm')
        
        try:
            self._wsman = WSMan(
                host,
                port=port,
                username=user,
                password=password,
                ssl=ssl,
                cert_validation=cert_validation if ssl else False,
                auth=auth,
                connection_timeout=30,
                read_timeout=60,
            )
            
            self._client = Client(
                host,
                port=port,
                username=user,
                password=password,
                ssl=ssl,
                cert_validation=cert_validation if ssl else False,
                auth=auth,
            )
            
        except Exception as e:
            from sansible.engine.errors import ConnectionError
            raise ConnectionError(
                host=self.host.name,
                message=str(e),
                connection_type='winrm'
            )
    
    async def close(self) -> None:
        """Close WinRM connection."""
        # pypsrp handles connection pooling, just clear references
        self._client = None
        self._wsman = None
    
    async def run(
        self,
        command: str,
        shell: bool = True,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
        environment: Optional[dict] = None,
    ) -> RunResult:
        """
        Run a command via PowerShell Remoting.
        
        Args:
            command: Command/script to execute
            shell: If True, run as PowerShell script; else as cmd command
            timeout: Optional timeout in seconds
            cwd: Working directory (prepends Set-Location)
            environment: Environment variables
            
        Returns:
            RunResult with rc, stdout, stderr
        """
        if not self._client:
            return RunResult(rc=1, stdout="", stderr="Not connected")
        
        # Build PowerShell script
        ps_script = ""
        
        # Set working directory
        if cwd:
            ps_script += f"Set-Location -Path '{cwd}'\n"
        
        # Set environment variables
        if environment:
            for key, value in environment.items():
                ps_script += f"$env:{key} = '{value}'\n"
        
        if shell:
            # Run as PowerShell script
            ps_script += command
        else:
            # Run as cmd.exe command
            ps_script += f"cmd.exe /c \"{command}\""
        
        # Execute in thread pool (pypsrp is synchronous)
        loop = asyncio.get_event_loop()
        
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._run_powershell, ps_script),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            return RunResult(
                rc=124,
                stdout="",
                stderr="Command timed out",
            )
    
    def _run_powershell(self, script: str) -> RunResult:
        """Synchronous PowerShell execution."""
        try:
            output, streams, had_errors = self._client.execute_ps(script)
            
            # pypsrp returns None for empty output, and streams is a PSDataStreams object
            stdout = output or ""
            
            # Extract error messages from streams.error
            stderr_parts = []
            if streams and hasattr(streams, 'error') and streams.error:
                for err in streams.error:
                    stderr_parts.append(str(err))
            stderr = "\n".join(stderr_parts)
            
            return RunResult(
                rc=1 if had_errors else 0,
                stdout=stdout,
                stderr=stderr,
            )
        except Exception as e:
            return RunResult(
                rc=1,
                stdout="",
                stderr=str(e),
            )
    
    async def put(
        self,
        local_path: Path,
        remote_path: str,
        mode: Optional[str] = None,
    ) -> None:
        """
        Upload a file via chunked base64 transfer.
        
        Uses PowerShell to receive base64-encoded chunks and reassemble.
        
        Args:
            local_path: Local file path
            remote_path: Remote destination path (Windows path)
            mode: Ignored on Windows
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, 
            self._sync_put, 
            local_path, 
            remote_path
        )
    
    def _sync_put(self, local_path: Path, remote_path: str) -> None:
        """Synchronous file upload."""
        # Normalize Windows path
        remote_path = remote_path.replace('/', '\\')
        
        # Ensure parent directory exists
        remote_dir = str(Path(remote_path).parent).replace('/', '\\')
        self._client.execute_ps(
            f"New-Item -ItemType Directory -Force -Path '{remote_dir}' | Out-Null"
        )
        
        # Read file and encode
        file_bytes = local_path.read_bytes()
        
        if len(file_bytes) == 0:
            # Empty file - just create it
            self._client.execute_ps(
                f"Set-Content -Path '{remote_path}' -Value '' -NoNewline"
            )
            return
        
        # Clear any existing file
        self._client.execute_ps(
            f"if (Test-Path '{remote_path}') {{ Remove-Item '{remote_path}' -Force }}"
        )
        
        # Transfer in chunks
        offset = 0
        while offset < len(file_bytes):
            chunk = file_bytes[offset:offset + CHUNK_SIZE]
            b64_chunk = base64.b64encode(chunk).decode('ascii')
            
            # Append chunk to file
            ps_script = f"""
$bytes = [Convert]::FromBase64String('{b64_chunk}')
$stream = [System.IO.File]::Open('{remote_path}', [System.IO.FileMode]::Append)
$stream.Write($bytes, 0, $bytes.Length)
$stream.Close()
"""
            stdout, stderr, had_errors = self._client.execute_ps(ps_script)
            
            if had_errors:
                raise RuntimeError(f"File upload failed: {stderr}")
            
            offset += CHUNK_SIZE
    
    async def get(
        self,
        remote_path: str,
        local_path: Path,
    ) -> None:
        """
        Download a file via chunked base64 transfer.
        
        Args:
            remote_path: Remote file path
            local_path: Local destination path
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._sync_get,
            remote_path,
            local_path
        )
    
    def _sync_get(self, remote_path: str, local_path: Path) -> None:
        """Synchronous file download."""
        remote_path = remote_path.replace('/', '\\')
        
        # Get file size first
        stdout, stderr, _ = self._client.execute_ps(
            f"(Get-Item '{remote_path}').Length"
        )
        file_size = int(stdout.strip()) if stdout.strip() else 0
        
        if file_size == 0:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(b'')
            return
        
        # Download in chunks
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(local_path, 'wb') as f:
            offset = 0
            while offset < file_size:
                chunk_size = min(CHUNK_SIZE, file_size - offset)
                
                ps_script = f"""
$stream = [System.IO.File]::OpenRead('{remote_path}')
$stream.Seek({offset}, [System.IO.SeekOrigin]::Begin) | Out-Null
$buffer = New-Object byte[] {chunk_size}
$stream.Read($buffer, 0, {chunk_size}) | Out-Null
$stream.Close()
[Convert]::ToBase64String($buffer)
"""
                stdout, stderr, had_errors = self._client.execute_ps(ps_script)
                
                if had_errors:
                    raise RuntimeError(f"File download failed: {stderr}")
                
                chunk_bytes = base64.b64decode(stdout.strip())
                f.write(chunk_bytes)
                
                offset += chunk_size
    
    async def mkdir(self, remote_path: str, mode: Optional[str] = None) -> None:
        """
        Create a directory via PowerShell.
        
        Args:
            remote_path: Directory path to create
            mode: Ignored on Windows
        """
        remote_path = remote_path.replace('/', '\\')
        await self.run(
            f"New-Item -ItemType Directory -Force -Path '{remote_path}' | Out-Null",
            shell=True
        )
    
    async def stat(self, remote_path: str) -> Optional[dict]:
        """
        Get file/directory information via PowerShell.
        
        Args:
            remote_path: Path to stat
            
        Returns:
            Dict with file info or None if not found
        """
        remote_path = remote_path.replace('/', '\\')
        
        ps_script = f"""
if (Test-Path '{remote_path}') {{
    $item = Get-Item '{remote_path}'
    @{{
        exists = $true
        isdir = $item.PSIsContainer
        isfile = -not $item.PSIsContainer
        size = if ($item.PSIsContainer) {{ 0 }} else {{ $item.Length }}
        mtime = ([DateTimeOffset]$item.LastWriteTime).ToUnixTimeSeconds()
    }} | ConvertTo-Json
}} else {{
    'null'
}}
"""
        result = await self.run(ps_script, shell=True)
        
        if result.rc != 0 or not result.stdout.strip() or result.stdout.strip() == 'null':
            return None
        
        import json
        try:
            data = json.loads(result.stdout)
            return {
                'exists': data.get('exists', False),
                'isdir': data.get('isdir', False),
                'isfile': data.get('isfile', False),
                'islink': False,  # Windows symlinks handled differently
                'size': data.get('size', 0),
                'mtime': data.get('mtime', 0),
            }
        except json.JSONDecodeError:
            return None
