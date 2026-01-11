"""
Sansible systemd module

Manage systemd services and units.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class SystemdModule(Module):
    """
    Control systemd services on a remote host.
    """
    
    name = "systemd"
    required_args = []
    optional_args = {
        "name": None,
        "state": None,  # started, stopped, restarted, reloaded
        "enabled": None,  # yes/no for boot enable
        "daemon_reload": False,
        "daemon_reexec": False,
        "scope": "system",  # system, user, global
        "no_block": False,
        "masked": None,
        "force": False,
    }
    
    async def run(self) -> ModuleResult:
        """Manage systemd service."""
        name = self.get_arg("name")
        state = self.get_arg("state")
        enabled = self.get_arg("enabled")
        daemon_reload = self.get_arg("daemon_reload", False)
        daemon_reexec = self.get_arg("daemon_reexec", False)
        scope = self.get_arg("scope", "system")
        no_block = self.get_arg("no_block", False)
        masked = self.get_arg("masked")
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        if not name and not daemon_reload and not daemon_reexec:
            return ModuleResult(
                failed=True,
                msg="name is required unless daemon_reload or daemon_reexec is true",
            )
        
        # Build systemctl base command
        systemctl = "systemctl"
        if scope == "user":
            systemctl = "systemctl --user"
        
        if no_block:
            systemctl += " --no-block"
        
        changed = False
        results = {}
        
        if self.context.check_mode:
            return ModuleResult(
                changed=True,
                msg="Would manage systemd service",
            )
        
        # Handle daemon-reload
        if daemon_reload:
            result = await self.connection.run(f"{systemctl} daemon-reload", shell=True)
            if result.rc != 0:
                return ModuleResult(
                    failed=True,
                    msg=f"Failed to reload daemon: {result.stderr}",
                )
            changed = True
        
        # Handle daemon-reexec
        if daemon_reexec:
            result = await self.connection.run(f"{systemctl} daemon-reexec", shell=True)
            if result.rc != 0:
                return ModuleResult(
                    failed=True,
                    msg=f"Failed to reexec daemon: {result.stderr}",
                )
            changed = True
        
        if not name:
            return ModuleResult(
                changed=changed,
                msg="Daemon operations completed",
            )
        
        # Get current state
        result = await self.connection.run(f"{systemctl} is-active '{name}' 2>/dev/null", shell=True)
        current_active = result.stdout.strip() == "active"
        
        result = await self.connection.run(f"{systemctl} is-enabled '{name}' 2>/dev/null", shell=True)
        current_enabled = result.stdout.strip() == "enabled"
        current_masked = result.stdout.strip() == "masked"
        
        results["name"] = name
        results["status"] = {
            "ActiveState": "active" if current_active else "inactive",
            "UnitFileState": "enabled" if current_enabled else ("masked" if current_masked else "disabled"),
        }
        
        # Handle masked state
        if masked is not None:
            if masked and not current_masked:
                result = await self.connection.run(f"{systemctl} mask '{name}'", shell=True)
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"Failed to mask service: {result.stderr}",
                    )
                changed = True
            elif not masked and current_masked:
                result = await self.connection.run(f"{systemctl} unmask '{name}'", shell=True)
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"Failed to unmask service: {result.stderr}",
                    )
                changed = True
        
        # Handle enabled state
        if enabled is not None:
            target_enabled = enabled in (True, "yes", "true")
            if target_enabled and not current_enabled:
                result = await self.connection.run(f"{systemctl} enable '{name}'", shell=True)
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"Failed to enable service: {result.stderr}",
                    )
                changed = True
            elif not target_enabled and current_enabled:
                result = await self.connection.run(f"{systemctl} disable '{name}'", shell=True)
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"Failed to disable service: {result.stderr}",
                    )
                changed = True
        
        # Handle state
        if state:
            if state == "started" and not current_active:
                result = await self.connection.run(f"{systemctl} start '{name}'", shell=True)
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"Failed to start service: {result.stderr}",
                    )
                changed = True
            elif state == "stopped" and current_active:
                result = await self.connection.run(f"{systemctl} stop '{name}'", shell=True)
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"Failed to stop service: {result.stderr}",
                    )
                changed = True
            elif state == "restarted":
                result = await self.connection.run(f"{systemctl} restart '{name}'", shell=True)
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"Failed to restart service: {result.stderr}",
                    )
                changed = True
            elif state == "reloaded":
                result = await self.connection.run(f"{systemctl} reload '{name}'", shell=True)
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"Failed to reload service: {result.stderr}",
                    )
                changed = True
        
        return ModuleResult(
            changed=changed,
            msg=f"Service {name} managed successfully",
            results=results,
        )


# Also register as systemd_service for Ansible compatibility
@register_module
class SystemdServiceModule(SystemdModule):
    """Alias for systemd module."""
    name = "systemd_service"
