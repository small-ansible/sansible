"""
Sansible wait_for module

Wait for a condition before continuing.
"""

import asyncio
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WaitForModule(Module):
    """
    Wait for a port to become available or a file to exist.
    
    Common use cases:
    - Wait for a service to start
    - Wait for a file to be created
    - Wait for a file to be removed (lock file)
    """
    
    name = "wait_for"
    required_args = []  # Either host+port or path required
    optional_args = {
        "host": "127.0.0.1",
        "port": None,
        "path": None,
        "state": "started",  # started, stopped, present, absent
        "delay": 0,  # Seconds to wait before first check
        "timeout": 300,  # Maximum seconds to wait
        "sleep": 1,  # Seconds between checks
    }
    
    async def run(self) -> ModuleResult:
        """Wait for condition."""
        host = self.args.get("host", "127.0.0.1")
        port = self.args.get("port")
        path = self.args.get("path")
        state = self.args.get("state", "started")
        delay = float(self.args.get("delay", 0))
        timeout = float(self.args.get("timeout", 300))
        sleep = float(self.args.get("sleep", 1))
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Validate - need port or path
        if port is None and path is None:
            return ModuleResult(
                failed=True,
                msg="Either 'port' or 'path' is required",
            )
        
        # Initial delay
        if delay > 0:
            await asyncio.sleep(delay)
        
        elapsed = 0
        
        while elapsed < timeout:
            if port is not None:
                success = await self._check_port(host, port, state)
            else:
                success = await self._check_path(path, state)
            
            if success:
                if port:
                    return ModuleResult(
                        changed=False,
                        msg=f"Port {port} is reachable",
                    )
                else:
                    return ModuleResult(
                        changed=False,
                        msg=f"Path {path} meets condition",
                    )
            
            await asyncio.sleep(sleep)
            elapsed += sleep
        
        # Timeout
        if port:
            return ModuleResult(
                failed=True,
                msg=f"Timed out waiting for port {port} on {host}",
            )
        else:
            return ModuleResult(
                failed=True,
                msg=f"Timed out waiting for path {path} to be {state}",
            )
    
    async def _check_port(self, host: str, port: int, state: str) -> bool:
        """Check if port is in desired state."""
        # Use nc or bash to check port
        cmd = f"nc -z {host} {port} 2>/dev/null || (echo 'x' > /dev/tcp/{host}/{port}) 2>/dev/null"
        
        try:
            result = await self.connection.run(cmd, shell=True)
            port_open = result.rc == 0
            
            if state in ("started", "present"):
                return port_open
            else:  # stopped, absent
                return not port_open
        except Exception:
            if state in ("started", "present"):
                return False
            return True
    
    async def _check_path(self, path: str, state: str) -> bool:
        """Check if path is in desired state."""
        cmd = f"test -e {path}"
        
        try:
            result = await self.connection.run(cmd, shell=True)
            exists = result.rc == 0
            
            if state in ("present", "started"):
                return exists
            else:  # absent, stopped
                return not exists
        except Exception:
            if state in ("present", "started"):
                return False
            return True
