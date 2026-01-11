"""
Sansible win_ping module

Ping Windows hosts to verify connectivity.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WinPingModule(Module):
    """
    Windows ping module to verify WinRM connectivity.
    
    Returns 'pong' on success, similar to the linux ping module.
    """
    
    name = "win_ping"
    required_args = []
    optional_args = {
        "data": "pong",
    }
    
    async def run(self) -> ModuleResult:
        """Ping Windows host."""
        data = self.get_arg("data", "pong")
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Execute a simple PowerShell command to verify connectivity
        result = await self.connection.run(
            f"Write-Output '{data}'",
            shell=True,
        )
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Ping failed: {result.stderr}",
            )
        
        return ModuleResult(
            changed=False,
            msg=data,
            results={"ping": data},
        )
