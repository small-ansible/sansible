"""
Sansible reboot module

Reboot a remote machine and wait for it to come back.
"""

import asyncio
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class RebootModule(Module):
    """
    Reboot a machine, wait for it to go down, come back up, and respond.
    """
    
    name = "reboot"
    required_args = []
    optional_args = {
        "msg": "Reboot initiated by Sansible",
        "pre_reboot_delay": 0,
        "post_reboot_delay": 0,
        "reboot_timeout": 600,
        "connect_timeout": 5,
        "test_command": "whoami",
    }
    
    async def run(self) -> ModuleResult:
        """Reboot remote machine and wait for it to return."""
        msg = self.get_arg("msg", "Reboot initiated by Sansible")
        pre_reboot_delay = int(self.get_arg("pre_reboot_delay", 0))
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
                msg="Would reboot the machine",
            )
        
        # Pre-reboot delay
        if pre_reboot_delay > 0:
            await asyncio.sleep(pre_reboot_delay)
        
        # Issue reboot command
        # Use shutdown command with schedule to allow the command to complete
        reboot_cmd = f"shutdown -r +0 '{msg}' &"
        
        # Try to issue reboot - don't wait for it or expect success
        try:
            await self.connection.run(reboot_cmd, shell=True)
        except Exception:
            # Connection may drop during reboot command - that's expected
            pass
        
        # Post-reboot delay before attempting reconnect
        if post_reboot_delay > 0:
            await asyncio.sleep(post_reboot_delay)
        else:
            # Give the machine a moment to start rebooting
            await asyncio.sleep(5)
        
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
            msg=f"Timeout waiting for machine to reboot after {reboot_timeout} seconds. Last error: {last_error}",
        )
