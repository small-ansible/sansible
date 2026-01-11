"""
Sansible wait_for_connection module

Wait for machine to become reachable.
"""

import asyncio
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WaitForConnectionModule(Module):
    """
    Wait for a machine to become reachable.
    
    Useful after reboot or after machine comes up.
    """
    
    name = "wait_for_connection"
    required_args = []
    optional_args = {
        "connect_timeout": 5,
        "delay": 0,
        "sleep": 1,
        "timeout": 600,
    }
    
    async def run(self) -> ModuleResult:
        """Wait for connection to become available."""
        connect_timeout = int(self.get_arg("connect_timeout", 5))
        delay = int(self.get_arg("delay", 0))
        sleep_interval = int(self.get_arg("sleep", 1))
        timeout = int(self.get_arg("timeout", 600))
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        if self.context.check_mode:
            return ModuleResult(
                changed=False,
                msg="Would wait for connection",
            )
        
        # Initial delay
        if delay > 0:
            await asyncio.sleep(delay)
        
        start_time = asyncio.get_event_loop().time()
        last_error = None
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                # Try to run a simple command to test connectivity
                result = await self.connection.run("echo pong", shell=True)
                if result.rc == 0 and "pong" in result.stdout:
                    elapsed = int(asyncio.get_event_loop().time() - start_time)
                    return ModuleResult(
                        changed=False,
                        msg=f"Connection established after {elapsed} seconds",
                        results={
                            "elapsed": elapsed,
                        },
                    )
            except Exception as e:
                last_error = str(e)
                # Try to reconnect
                try:
                    await self.connection.close()
                except Exception:
                    pass
                try:
                    await self.connection.connect()
                except Exception:
                    pass
            
            await asyncio.sleep(sleep_interval)
        
        return ModuleResult(
            failed=True,
            msg=f"Timeout waiting for connection after {timeout} seconds. Last error: {last_error}",
        )
