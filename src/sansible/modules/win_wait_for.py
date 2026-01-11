"""
Sansible win_wait_for module

Wait for a condition before continuing (Windows).
"""

import asyncio
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WinWaitForModule(Module):
    """
    Wait for a port or file on Windows.
    
    Uses PowerShell for checks.
    """
    
    name = "win_wait_for"
    required_args = []
    optional_args = {
        "host": "127.0.0.1",
        "port": None,
        "path": None,
        "state": "started",
        "delay": 0,
        "timeout": 300,
        "sleep": 1,
    }
    
    async def run(self) -> ModuleResult:
        """Wait for condition on Windows."""
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
        
        if port is None and path is None:
            return ModuleResult(
                failed=True,
                msg="Either 'port' or 'path' is required",
            )
        
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
        """Check if port is available using PowerShell."""
        ps_cmd = f'''
$tcp = New-Object System.Net.Sockets.TcpClient
try {{
    $tcp.Connect("{host}", {port})
    $tcp.Close()
    exit 0
}} catch {{
    exit 1
}}
'''
        try:
            result = await self.connection.run(ps_cmd, shell=True)
            port_open = result.rc == 0
            
            if state in ("started", "present"):
                return port_open
            else:
                return not port_open
        except Exception:
            if state in ("started", "present"):
                return False
            return True
    
    async def _check_path(self, path: str, state: str) -> bool:
        """Check if path exists using PowerShell."""
        ps_cmd = f'if (Test-Path -LiteralPath "{path}") {{ exit 0 }} else {{ exit 1 }}'
        
        try:
            result = await self.connection.run(ps_cmd, shell=True)
            exists = result.rc == 0
            
            if state in ("present", "started"):
                return exists
            else:
                return not exists
        except Exception:
            if state in ("present", "started"):
                return False
            return True
