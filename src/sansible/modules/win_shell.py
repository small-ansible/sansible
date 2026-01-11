"""
Sansible win_shell module

Execute PowerShell commands on Windows hosts.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WinShellModule(Module):
    """
    Execute PowerShell commands on Windows hosts.
    
    Commands are processed through PowerShell, supporting full
    PowerShell syntax, pipes, and variables.
    """
    
    name = "win_shell"
    required_args = []
    optional_args = {
        "chdir": None,
        "creates": None,
        "removes": None,
        "executable": None,  # Custom shell (default: powershell.exe)
        "no_profile": False,
    }
    
    def validate_args(self) -> str | None:
        if "_raw_params" not in self.args and "cmd" not in self.args:
            return "Either free-form command or 'cmd' argument is required"
        return None
    
    async def run(self) -> ModuleResult:
        """Execute the PowerShell command."""
        cmd = self.args.get("_raw_params") or self.args.get("cmd", "")
        chdir = self.get_arg("chdir")
        creates = self.get_arg("creates")
        removes = self.get_arg("removes")
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Check 'creates' - skip if file exists
        if creates:
            stat_result = await self.connection.stat(creates)
            if stat_result and stat_result.get("exists"):
                return ModuleResult(
                    changed=False,
                    msg=f"skipped, since {creates} exists",
                    skipped=True,
                )
        
        # Check 'removes' - skip if file doesn't exist
        if removes:
            stat_result = await self.connection.stat(removes)
            if not stat_result or not stat_result.get("exists"):
                return ModuleResult(
                    changed=False,
                    msg=f"skipped, since {removes} does not exist",
                    skipped=True,
                )
        
        # Execute PowerShell command directly
        result = await self.connection.run(
            cmd,
            shell=True,  # Use PowerShell
            cwd=chdir,
        )
        
        return ModuleResult(
            changed=True,
            rc=result.rc,
            stdout=result.stdout,
            stderr=result.stderr,
            failed=result.rc != 0,
            msg=f"non-zero return code: {result.rc}" if result.rc != 0 else "",
        )
