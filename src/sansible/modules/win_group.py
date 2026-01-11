"""
Sansible win_group module

Manage Windows local groups.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WinGroupModule(Module):
    """
    Manage local Windows groups.
    """
    
    name = "win_group"
    required_args = ["name"]
    optional_args = {
        "state": "present",
        "description": None,
    }
    
    async def run(self) -> ModuleResult:
        """Manage Windows group."""
        name = self.args["name"]
        state = self.get_arg("state", "present")
        description = self.get_arg("description")
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Check if group exists
        check_cmd = f"""
$group = Get-LocalGroup -Name '{name}' -ErrorAction SilentlyContinue
if ($group) {{ 'exists' }} else {{ 'absent' }}
"""
        result = await self.connection.run(check_cmd, shell=True)
        group_exists = 'exists' in result.stdout.strip()
        
        changed = False
        
        if self.context.check_mode:
            if state == "absent" and group_exists:
                return ModuleResult(changed=True, msg=f"Would remove group {name}")
            elif state == "present" and not group_exists:
                return ModuleResult(changed=True, msg=f"Would create group {name}")
            return ModuleResult(changed=False, msg=f"Group {name} would be unchanged")
        
        if state == "absent":
            if group_exists:
                delete_cmd = f"Remove-LocalGroup -Name '{name}'"
                result = await self.connection.run(delete_cmd, shell=True)
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"Failed to remove group: {result.stderr}",
                    )
                changed = True
        else:  # state == present
            if not group_exists:
                # Create group
                create_cmd = f"New-LocalGroup -Name '{name}'"
                if description:
                    create_cmd += f" -Description '{description}'"
                
                result = await self.connection.run(create_cmd, shell=True)
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"Failed to create group: {result.stderr}",
                    )
                changed = True
            else:
                # Update group description if provided
                if description is not None:
                    # Get current description
                    get_desc_cmd = f"(Get-LocalGroup -Name '{name}').Description"
                    result = await self.connection.run(get_desc_cmd, shell=True)
                    current_desc = result.stdout.strip()
                    
                    if current_desc != description:
                        set_desc_cmd = f"Set-LocalGroup -Name '{name}' -Description '{description}'"
                        result = await self.connection.run(set_desc_cmd, shell=True)
                        if result.rc == 0:
                            changed = True
        
        return ModuleResult(
            changed=changed,
            msg=f"Group {name} {'created' if not group_exists and state == 'present' else 'removed' if state == 'absent' and group_exists else 'updated' if changed else 'unchanged'}",
            results={"name": name, "state": state},
        )
