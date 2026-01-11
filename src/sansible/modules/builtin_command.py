"""
Sansible command module

Execute commands without shell processing.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class CommandModule(Module):
    """
    Execute commands on target hosts.
    
    Unlike shell, this module does not process commands through a shell,
    so shell operators and variables won't work.
    """
    
    name = "command"
    required_args = []  # Either _raw_params or cmd
    optional_args = {
        "chdir": None,
        "creates": None,
        "removes": None,
        "warn": True,
    }
    
    def validate_args(self) -> str | None:
        if "_raw_params" not in self.args and "cmd" not in self.args:
            return "Either free-form command or 'cmd' argument is required"
        return None
    
    async def run(self) -> ModuleResult:
        """Execute the command."""
        cmd = self.args.get("_raw_params") or self.args.get("cmd", "")
        chdir = self.get_arg("chdir")
        creates = self.get_arg("creates")
        removes = self.get_arg("removes")
        
        # Check 'creates' - skip if file exists
        if creates and self.connection:
            stat_result = await self.connection.stat(creates)
            if stat_result and stat_result.get("exists"):
                return ModuleResult(
                    changed=False,
                    msg=f"skipped, since {creates} exists",
                    skipped=True,
                )
        
        # Check 'removes' - skip if file doesn't exist
        if removes and self.connection:
            stat_result = await self.connection.stat(removes)
            if not stat_result or not stat_result.get("exists"):
                return ModuleResult(
                    changed=False,
                    msg=f"skipped, since {removes} does not exist",
                    skipped=True,
                )
        
        # Check mode - skip execution
        if self.context.check_mode:
            return ModuleResult(
                changed=True,
                skipped=True,
                msg="command would be executed (check mode)",
            )
        
        # Execute command
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Wrap with become (sudo/su) if needed
        exec_cmd = self.wrap_become(cmd)
        
        result = await self.connection.run(
            exec_cmd,
            shell=False,  # command module doesn't use shell
            cwd=chdir,
        )
        
        return ModuleResult(
            changed=True,  # Commands always report changed
            rc=result.rc,
            stdout=result.stdout,
            stderr=result.stderr,
            failed=result.rc != 0,
            msg=f"non-zero return code: {result.rc}" if result.rc != 0 else "",
        )
