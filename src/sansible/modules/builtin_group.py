"""
Sansible group module

Manage groups on Linux/Unix systems.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class GroupModule(Module):
    """
    Manage groups.
    
    Supports creating, modifying, and removing groups.
    """
    
    name = "group"
    required_args = ["name"]
    optional_args = {
        "state": "present",     # present, absent
        "gid": None,            # Group ID
        "system": False,        # System group
        "force": False,         # Force removal
    }
    
    async def run(self) -> ModuleResult:
        """Manage the group."""
        name = self.args["name"]
        state = self.get_arg("state", "present")
        
        if self.context.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"Group '{name}' would be modified (check mode)",
            )
        
        # Check if group exists
        exists = await self._group_exists(name)
        
        if state == "present":
            if exists:
                return await self._modify_group(name)
            else:
                return await self._create_group(name)
        elif state == "absent":
            if not exists:
                return ModuleResult(
                    changed=False,
                    msg=f"Group '{name}' does not exist",
                )
            return await self._remove_group(name)
        else:
            return ModuleResult(
                failed=True,
                msg=f"Unknown state: {state}. Valid: present, absent",
            )
    
    async def _group_exists(self, name: str) -> bool:
        """Check if group exists."""
        result = await self.connection.run(f"getent group {name}")
        return result.rc == 0
    
    async def _get_group_info(self, name: str) -> dict | None:
        """Get current group information."""
        result = await self.connection.run(f"getent group {name}")
        if result.rc != 0:
            return None
        
        parts = result.stdout.strip().split(":")
        if len(parts) >= 3:
            return {
                "name": parts[0],
                "gid": int(parts[2]),
            }
        return None
    
    async def _create_group(self, name: str) -> ModuleResult:
        """Create a new group."""
        cmd_parts = ["groupadd"]
        
        gid = self.get_arg("gid")
        if gid:
            cmd_parts.extend(["-g", str(gid)])
        
        if self.get_arg("system"):
            cmd_parts.append("-r")
        
        cmd_parts.append(name)
        cmd = " ".join(cmd_parts)
        cmd = self.wrap_become(cmd)
        
        result = await self.connection.run(cmd)
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to create group '{name}': {result.stderr}",
            )
        
        return ModuleResult(
            changed=True,
            msg=f"Group '{name}' created",
            results={"name": name, "state": "present"},
        )
    
    async def _modify_group(self, name: str) -> ModuleResult:
        """Modify existing group."""
        current = await self._get_group_info(name)
        if not current:
            return ModuleResult(
                failed=True,
                msg=f"Failed to get info for group '{name}'",
            )
        
        gid = self.get_arg("gid")
        if gid and gid != current["gid"]:
            cmd = f"groupmod -g {gid} {name}"
            cmd = self.wrap_become(cmd)
            
            result = await self.connection.run(cmd)
            if result.rc != 0:
                return ModuleResult(
                    failed=True,
                    msg=f"Failed to modify group '{name}': {result.stderr}",
                )
            
            return ModuleResult(
                changed=True,
                msg=f"Group '{name}' gid changed to {gid}",
            )
        
        return ModuleResult(
            changed=False,
            msg=f"Group '{name}' already up to date",
        )
    
    async def _remove_group(self, name: str) -> ModuleResult:
        """Remove the group."""
        cmd = f"groupdel {name}"
        if self.get_arg("force"):
            cmd = f"groupdel -f {name}"
        cmd = self.wrap_become(cmd)
        
        result = await self.connection.run(cmd)
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to remove group '{name}': {result.stderr}",
            )
        
        return ModuleResult(
            changed=True,
            msg=f"Group '{name}' removed",
        )
