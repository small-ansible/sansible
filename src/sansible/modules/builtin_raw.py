"""
Sansible raw module

Execute raw commands without module processing.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class RawModule(Module):
    """
    Execute raw commands without module wrapping.
    
    This module bypasses the module subsystem and executes commands
    directly on the remote host. Useful for edge cases where modules
    can't be used (e.g., installing Python on a target).
    """
    
    name = "raw"
    required_args = []
    optional_args = {
        "executable": None,
    }
    
    def validate_args(self) -> str | None:
        if "_raw_params" not in self.args:
            return "Free-form command is required"
        return None
    
    async def run(self) -> ModuleResult:
        """Execute the raw command."""
        cmd = self.args.get("_raw_params", "")
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Raw commands go directly to the connection
        result = await self.connection.run(
            cmd,
            shell=True,
        )
        
        return ModuleResult(
            changed=True,
            rc=result.rc,
            stdout=result.stdout,
            stderr=result.stderr,
            failed=result.rc != 0,
            msg=f"non-zero return code: {result.rc}" if result.rc != 0 else "",
        )
