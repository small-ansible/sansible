"""
Sansible hostname module

Manage the system hostname.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class HostnameModule(Module):
    """
    Set the system hostname.
    """
    
    name = "hostname"
    required_args = ["name"]
    optional_args = {
        "use": None,  # Strategy: systemd, debian, rhel, etc.
    }
    
    async def run(self) -> ModuleResult:
        """Set system hostname."""
        name = self.args["name"]
        use = self.get_arg("use")
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Get current hostname
        result = await self.connection.run("hostname", shell=True)
        current_hostname = result.stdout.strip() if result.rc == 0 else ""
        
        if current_hostname == name:
            return ModuleResult(
                changed=False,
                msg=f"Hostname is already {name}",
            )
        
        if self.context.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"Would change hostname from {current_hostname} to {name}",
            )
        
        # Try different methods to set hostname
        commands = []
        
        if use == "systemd":
            commands = [f"hostnamectl set-hostname '{name}'"]
        elif use == "debian":
            commands = [
                f"echo '{name}' > /etc/hostname",
                f"hostname '{name}'",
            ]
        elif use == "rhel":
            commands = [
                f"hostnamectl set-hostname '{name}'",
            ]
        else:
            # Auto-detect: try hostnamectl first, then fallback
            commands = [
                f"hostnamectl set-hostname '{name}' 2>/dev/null || (echo '{name}' > /etc/hostname && hostname '{name}')",
            ]
        
        for cmd in commands:
            result = await self.connection.run(cmd, shell=True)
            if result.rc != 0:
                return ModuleResult(
                    failed=True,
                    msg=f"Failed to set hostname: {result.stderr}",
                )
        
        return ModuleResult(
            changed=True,
            msg=f"Hostname changed from {current_hostname} to {name}",
            results={
                "name": name,
                "old_name": current_hostname,
            },
        )
