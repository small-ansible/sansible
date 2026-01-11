"""
Sansible Local Connection

Execute commands on the local machine (no remote connection).
"""

import asyncio
import os
import shutil
import stat
from pathlib import Path
from typing import Optional

from sansible.connections.base import Connection, RunResult
from sansible.engine.inventory import Host


class LocalConnection(Connection):
    """
    Local connection - execute commands on the control node.
    
    Used for localhost execution without any network operations.
    """
    
    def __init__(self, host: Host):
        super().__init__(host)
        self._connected = False
    
    async def connect(self) -> None:
        """Local connection is always available."""
        self._connected = True
    
    async def close(self) -> None:
        """Nothing to close for local connection."""
        self._connected = False
    
    async def run(
        self,
        command: str,
        shell: bool = True,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
        environment: Optional[dict] = None,
    ) -> RunResult:
        """
        Run a command locally.
        
        Args:
            command: Command to execute
            shell: If True, run through a shell
            timeout: Optional timeout in seconds
            cwd: Working directory
            environment: Environment variables
            
        Returns:
            RunResult with rc, stdout, stderr
        """
        # Prepare environment
        env = os.environ.copy()
        if environment:
            env.update(environment)
        
        try:
            if shell:
                # Run through shell
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=env,
                )
            else:
                # Run directly (command should be a list, but we'll split)
                import shlex
                args = shlex.split(command)
                process = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=env,
                )
            
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return RunResult(
                    rc=124,  # Standard timeout exit code
                    stdout="",
                    stderr="Command timed out",
                )
            
            return RunResult(
                rc=process.returncode or 0,
                stdout=stdout_bytes.decode('utf-8', errors='replace'),
                stderr=stderr_bytes.decode('utf-8', errors='replace'),
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
        Copy a file locally.
        
        Args:
            local_path: Source file path
            remote_path: Destination path
            mode: Optional file mode
        """
        dest = Path(remote_path)
        
        # Ensure parent directory exists
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy the file
        shutil.copy2(local_path, dest)
        
        # Set mode if specified
        if mode:
            os.chmod(dest, int(mode, 8))
    
    async def get(
        self,
        remote_path: str,
        local_path: Path,
    ) -> None:
        """
        Copy a file locally.
        
        Args:
            remote_path: Source file path
            local_path: Destination path
        """
        src = Path(remote_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, local_path)
    
    async def mkdir(self, remote_path: str, mode: Optional[str] = None) -> None:
        """
        Create a directory locally.
        
        Args:
            remote_path: Directory path to create
            mode: Optional directory mode
        """
        path = Path(remote_path)
        if mode:
            path.mkdir(parents=True, exist_ok=True, mode=int(mode, 8))
        else:
            path.mkdir(parents=True, exist_ok=True)
    
    async def stat(self, remote_path: str) -> Optional[dict]:
        """
        Get file/directory information.
        
        Args:
            remote_path: Path to stat
            
        Returns:
            Dict with file info or None if not found
        """
        path = Path(remote_path)
        
        if not path.exists():
            return None
        
        st = path.stat()
        return {
            'exists': True,
            'isdir': path.is_dir(),
            'isfile': path.is_file(),
            'islink': path.is_symlink(),
            'size': st.st_size,
            'mtime': st.st_mtime,
            'mode': oct(st.st_mode)[-4:],
            'uid': st.st_uid,
            'gid': st.st_gid,
        }
