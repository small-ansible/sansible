"""
Sansible service module

Manage services on Linux/Unix systems.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class ServiceModule(Module):
    """
    Manage services (start, stop, restart, enable, disable).
    
    Supports systemd, sysvinit, and other service managers.
    """
    
    name = "service"
    required_args = ["name"]
    optional_args = {
        "state": None,      # started, stopped, restarted, reloaded
        "enabled": None,    # yes/no
        "pattern": None,    # Pattern to match in ps output
        "sleep": None,      # Seconds to sleep between stop and start for restart
        "use": None,        # Service module to use (auto, systemd, sysvinit)
    }
    
    async def run(self) -> ModuleResult:
        """Manage the service."""
        name = self.args["name"]
        state = self.get_arg("state")
        enabled = self.get_arg("enabled")
        
        if not state and enabled is None:
            return ModuleResult(
                failed=True,
                msg="Either 'state' or 'enabled' must be specified",
            )
        
        if self.context.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"Service '{name}' would be modified (check mode)",
            )
        
        changed = False
        messages = []
        
        # Detect service manager
        service_mgr = await self._detect_service_manager()
        
        # Handle state changes
        if state:
            if state == "started":
                changed, msg = await self._ensure_started(name, service_mgr)
            elif state == "stopped":
                changed, msg = await self._ensure_stopped(name, service_mgr)
            elif state == "restarted":
                changed, msg = await self._restart(name, service_mgr)
            elif state == "reloaded":
                changed, msg = await self._reload(name, service_mgr)
            else:
                return ModuleResult(
                    failed=True,
                    msg=f"Unknown state: {state}. Valid: started, stopped, restarted, reloaded",
                )
            messages.append(msg)
        
        # Handle enabled changes
        if enabled is not None:
            enabled_changed, msg = await self._set_enabled(name, enabled, service_mgr)
            changed = changed or enabled_changed
            messages.append(msg)
        
        return ModuleResult(
            changed=changed,
            msg="; ".join(messages),
            results={"name": name, "state": state, "enabled": enabled},
        )
    
    async def _detect_service_manager(self) -> str:
        """Detect which service manager is available."""
        # Check for systemd
        result = await self.connection.run("command -v systemctl")
        if result.rc == 0:
            return "systemd"
        
        # Check for sysvinit
        result = await self.connection.run("command -v service")
        if result.rc == 0:
            return "sysvinit"
        
        # Fallback
        return "unknown"
    
    async def _get_service_status(self, name: str, mgr: str) -> bool:
        """Check if service is running."""
        if mgr == "systemd":
            result = await self.connection.run(f"systemctl is-active {name}")
            return result.rc == 0
        else:
            result = await self.connection.run(f"service {name} status")
            return result.rc == 0
    
    async def _ensure_started(self, name: str, mgr: str) -> tuple[bool, str]:
        """Ensure service is started."""
        is_running = await self._get_service_status(name, mgr)
        if is_running:
            return False, f"Service '{name}' already running"
        
        if mgr == "systemd":
            cmd = f"systemctl start {name}"
        else:
            cmd = f"service {name} start"
        
        cmd = self.wrap_become(cmd)
        result = await self.connection.run(cmd)
        if result.rc != 0:
            return False, f"Failed to start '{name}': {result.stderr}"
        
        return True, f"Service '{name}' started"
    
    async def _ensure_stopped(self, name: str, mgr: str) -> tuple[bool, str]:
        """Ensure service is stopped."""
        is_running = await self._get_service_status(name, mgr)
        if not is_running:
            return False, f"Service '{name}' already stopped"
        
        if mgr == "systemd":
            cmd = f"systemctl stop {name}"
        else:
            cmd = f"service {name} stop"
        
        cmd = self.wrap_become(cmd)
        result = await self.connection.run(cmd)
        if result.rc != 0:
            return False, f"Failed to stop '{name}': {result.stderr}"
        
        return True, f"Service '{name}' stopped"
    
    async def _restart(self, name: str, mgr: str) -> tuple[bool, str]:
        """Restart the service."""
        if mgr == "systemd":
            cmd = f"systemctl restart {name}"
        else:
            cmd = f"service {name} restart"
        
        cmd = self.wrap_become(cmd)
        result = await self.connection.run(cmd)
        if result.rc != 0:
            return False, f"Failed to restart '{name}': {result.stderr}"
        
        return True, f"Service '{name}' restarted"
    
    async def _reload(self, name: str, mgr: str) -> tuple[bool, str]:
        """Reload the service."""
        if mgr == "systemd":
            cmd = f"systemctl reload {name}"
        else:
            cmd = f"service {name} reload"
        
        cmd = self.wrap_become(cmd)
        result = await self.connection.run(cmd)
        if result.rc != 0:
            return False, f"Failed to reload '{name}': {result.stderr}"
        
        return True, f"Service '{name}' reloaded"
    
    async def _set_enabled(self, name: str, enabled: bool, mgr: str) -> tuple[bool, str]:
        """Enable or disable the service."""
        action = "enable" if enabled else "disable"
        
        if mgr == "systemd":
            # Check current state
            check_result = await self.connection.run(f"systemctl is-enabled {name}")
            is_enabled = check_result.rc == 0
            
            if is_enabled == enabled:
                return False, f"Service '{name}' already {'enabled' if enabled else 'disabled'}"
            
            cmd = f"systemctl {action} {name}"
        else:
            cmd = f"update-rc.d {name} {action}"
        
        cmd = self.wrap_become(cmd)
        result = await self.connection.run(cmd)
        if result.rc != 0:
            return False, f"Failed to {action} '{name}': {result.stderr}"
        
        return True, f"Service '{name}' {action}d"
