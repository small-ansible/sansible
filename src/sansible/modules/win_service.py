"""
Sansible win_service module

Manage Windows services via PowerShell.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WinServiceModule(Module):
    """
    Manage Windows services.
    
    Supports:
    - Starting/stopping/restarting services
    - Setting startup type (start_mode)
    - Checking service state
    
    Uses PowerShell Get-Service, Start-Service, Stop-Service, Set-Service.
    """
    
    name = "win_service"
    required_args = ["name"]
    optional_args = {
        "state": None,  # started, stopped, restarted, paused, absent
        "start_mode": None,  # auto, delayed, disabled, manual
        "force_dependent_services": False,
    }
    
    async def run(self) -> ModuleResult:
        """Execute the win_service operation."""
        name = self.args["name"]
        state = self.get_arg("state")
        start_mode = self.get_arg("start_mode")
        force = self.get_arg("force_dependent_services", False)
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Check mode - report what would happen
        if self.context.check_mode:
            msg_parts = []
            if state:
                msg_parts.append(f"state={state}")
            if start_mode:
                msg_parts.append(f"start_mode={start_mode}")
            return ModuleResult(
                changed=True,
                msg=f"Service '{name}' would be set to {', '.join(msg_parts)} (check mode)",
                results={"name": name, "state": state, "start_mode": start_mode},
            )
        
        # Get current service state
        current_state = await self._get_service_state(name)
        
        if current_state is None:
            # Service doesn't exist
            if state == "absent":
                return ModuleResult(
                    changed=False,
                    msg=f"Service '{name}' does not exist",
                    results={"name": name, "exists": False},
                )
            return ModuleResult(
                failed=True,
                msg=f"Service '{name}' not found",
                results={"name": name, "exists": False},
            )
        
        changed = False
        
        # Handle state changes
        if state:
            state_changed = await self._ensure_state(name, state, current_state, force)
            changed = changed or state_changed
        
        # Handle start_mode changes
        if start_mode:
            mode_changed = await self._ensure_start_mode(name, start_mode)
            changed = changed or mode_changed
        
        return ModuleResult(
            changed=changed,
            msg=f"Service '{name}' configured successfully",
            results={
                "name": name,
                "exists": True,
                "state": state or current_state,
                "start_mode": start_mode,
            },
        )
    
    async def _get_service_state(self, name: str) -> str | None:
        """Get current service state via PowerShell."""
        cmd = f"Get-Service -Name '{name}' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status"
        result = await self.connection.run(cmd, shell=True)
        
        if result.rc != 0 or not result.stdout.strip():
            return None
        
        state = result.stdout.strip().lower()
        # Map PowerShell states to Ansible states
        state_map = {
            "running": "running",
            "stopped": "stopped",
            "paused": "paused",
            "startpending": "starting",
            "stoppending": "stopping",
        }
        return state_map.get(state, state)
    
    async def _ensure_state(self, name: str, desired: str, current: str, force: bool) -> bool:
        """Ensure service is in the desired state."""
        force_flag = "-Force" if force else ""
        
        if desired == "started":
            if current == "running":
                return False  # Already running
            cmd = f"Start-Service -Name '{name}' {force_flag}"
        elif desired == "stopped":
            if current == "stopped":
                return False  # Already stopped
            cmd = f"Stop-Service -Name '{name}' {force_flag}"
        elif desired == "restarted":
            cmd = f"Restart-Service -Name '{name}' {force_flag}"
        elif desired == "paused":
            if current == "paused":
                return False
            cmd = f"Suspend-Service -Name '{name}'"
        elif desired == "absent":
            cmd = f"Remove-Service -Name '{name}' {force_flag}"
        else:
            return False
        
        result = await self.connection.run(cmd, shell=True)
        return result.rc == 0
    
    async def _ensure_start_mode(self, name: str, start_mode: str) -> bool:
        """Set service startup type."""
        # Map Ansible start_mode to PowerShell StartupType
        mode_map = {
            "auto": "Automatic",
            "automatic": "Automatic",
            "delayed": "AutomaticDelayedStart",
            "disabled": "Disabled",
            "manual": "Manual",
        }
        ps_mode = mode_map.get(start_mode.lower(), start_mode)
        
        cmd = f"Set-Service -Name '{name}' -StartupType '{ps_mode}'"
        result = await self.connection.run(cmd, shell=True)
        return result.rc == 0
