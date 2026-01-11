"""
Sansible win_reboot module

Reboot Windows machines and wait for them to come back.
"""

import asyncio
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WinRebootModule(Module):
    """
    Reboot a Windows machine and wait for it to come back.
    """
    
    name = "win_reboot"
    required_args = []
    optional_args = {
        "msg": "Reboot initiated by Sansible",
        "pre_reboot_delay": 2,
        "post_reboot_delay": 0,
        "reboot_timeout": 600,
        "connect_timeout": 5,
        "test_command": "whoami",
    }
    
    async def run(self) -> ModuleResult:
        """Reboot Windows machine and wait for it to return."""
        msg = self.get_arg("msg", "Reboot initiated by Sansible")
        pre_reboot_delay = int(self.get_arg("pre_reboot_delay", 2))
        post_reboot_delay = int(self.get_arg("post_reboot_delay", 0))
        reboot_timeout = int(self.get_arg("reboot_timeout", 600))
        connect_timeout = int(self.get_arg("connect_timeout", 5))
        test_command = self.get_arg("test_command", "whoami")
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        if self.context.check_mode:
            return ModuleResult(
                changed=True,
                msg="Would reboot the Windows machine",
            )
        
        # Issue reboot command using PowerShell
        # Use shutdown.exe with /r for restart, /t for timeout, /c for comment
        reboot_cmd = f"shutdown.exe /r /t {pre_reboot_delay} /c \"{msg}\""
        
        # Issue the reboot command
        try:
            await self.connection.run(reboot_cmd, shell=True)
        except Exception:
            # Connection may drop during reboot - that's expected
            pass
        
        # Post-reboot delay before attempting reconnect
        if post_reboot_delay > 0:
            await asyncio.sleep(post_reboot_delay)
        else:
            # Give the machine a moment to start rebooting
            await asyncio.sleep(pre_reboot_delay + 5)
        
        # Wait for machine to come back up
        start_time = asyncio.get_event_loop().time()
        last_error = None
        
        while (asyncio.get_event_loop().time() - start_time) < reboot_timeout:
            try:
                # Try to reconnect
                await self.connection.close()
                await self.connection.connect()
                
                # Test connection
                result = await self.connection.run(test_command, shell=True)
                if result.rc == 0:
                    elapsed = int(asyncio.get_event_loop().time() - start_time)
                    return ModuleResult(
                        changed=True,
                        msg=f"Reboot completed in {elapsed} seconds",
                        results={
                            "rebooted": True,
                            "elapsed": elapsed,
                        },
                    )
            except Exception as e:
                last_error = str(e)
            
            # Wait before retrying
            await asyncio.sleep(connect_timeout)
        
        return ModuleResult(
            failed=True,
            msg=f"Timeout waiting for Windows to reboot after {reboot_timeout} seconds. Last error: {last_error}",
        )
