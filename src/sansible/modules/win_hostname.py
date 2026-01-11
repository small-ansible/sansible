"""
Sansible win_hostname module

Manage Windows hostname.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WinHostnameModule(Module):
    """
    Set the hostname of a Windows machine.
    """
    
    name = "win_hostname"
    required_args = ["name"]
    optional_args = {}
    
    async def run(self) -> ModuleResult:
        """Set Windows hostname."""
        name = self.args["name"]
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Get current hostname
        result = await self.connection.run("$env:COMPUTERNAME", shell=True)
        current_hostname = result.stdout.strip() if result.rc == 0 else ""
        
        if current_hostname.lower() == name.lower():
            return ModuleResult(
                changed=False,
                msg=f"Hostname is already {name}",
            )
        
        if self.context.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"Would change hostname from {current_hostname} to {name}",
                results={"reboot_required": True},
            )
        
        # Set hostname using Rename-Computer
        rename_cmd = f"Rename-Computer -NewName '{name}' -Force"
        
        result = await self.connection.run(rename_cmd, shell=True)
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to set hostname: {result.stderr}",
            )
        
        return ModuleResult(
            changed=True,
            msg=f"Hostname changed from {current_hostname} to {name}. Reboot required.",
            results={
                "name": name,
                "old_name": current_hostname,
                "reboot_required": True,
            },
        )
