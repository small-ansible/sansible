"""
Sansible win_user module

Manage Windows user accounts.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WinUserModule(Module):
    """
    Manage local Windows user accounts.
    """
    
    name = "win_user"
    required_args = ["name"]
    optional_args = {
        "password": None,
        "state": "present",
        "groups": [],
        "groups_action": "replace",  # add, remove, replace
        "description": None,
        "fullname": None,
        "home_directory": None,
        "account_disabled": False,
        "account_locked": False,
        "password_expired": False,
        "password_never_expires": False,
        "user_cannot_change_password": False,
        "update_password": "always",  # always, on_create
    }
    
    async def run(self) -> ModuleResult:
        """Manage Windows user."""
        name = self.args["name"]
        password = self.get_arg("password")
        state = self.get_arg("state", "present")
        groups = self.get_arg("groups", [])
        groups_action = self.get_arg("groups_action", "replace")
        description = self.get_arg("description")
        fullname = self.get_arg("fullname")
        account_disabled = self.get_arg("account_disabled", False)
        password_expired = self.get_arg("password_expired", False)
        password_never_expires = self.get_arg("password_never_expires", False)
        update_password = self.get_arg("update_password", "always")
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Check if user exists
        check_cmd = f"""
$user = Get-LocalUser -Name '{name}' -ErrorAction SilentlyContinue
if ($user) {{ 'exists' }} else {{ 'absent' }}
"""
        result = await self.connection.run(check_cmd, shell=True)
        user_exists = 'exists' in result.stdout.strip()
        
        changed = False
        
        if self.context.check_mode:
            if state == "absent" and user_exists:
                return ModuleResult(changed=True, msg=f"Would remove user {name}")
            elif state == "present" and not user_exists:
                return ModuleResult(changed=True, msg=f"Would create user {name}")
            return ModuleResult(changed=False, msg=f"User {name} would be unchanged")
        
        if state == "absent":
            if user_exists:
                delete_cmd = f"Remove-LocalUser -Name '{name}'"
                result = await self.connection.run(delete_cmd, shell=True)
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"Failed to remove user: {result.stderr}",
                    )
                changed = True
        else:  # state == present
            if not user_exists:
                # Create user
                create_cmd = f"$pass = ConvertTo-SecureString '{password or 'P@ssw0rd'}' -AsPlainText -Force; New-LocalUser -Name '{name}' -Password $pass"
                if description:
                    create_cmd += f" -Description '{description}'"
                if fullname:
                    create_cmd += f" -FullName '{fullname}'"
                
                result = await self.connection.run(create_cmd, shell=True)
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"Failed to create user: {result.stderr}",
                    )
                changed = True
            else:
                # Update user
                updates = []
                if password and update_password == "always":
                    updates.append(f"$pass = ConvertTo-SecureString '{password}' -AsPlainText -Force; Set-LocalUser -Name '{name}' -Password $pass")
                if description is not None:
                    updates.append(f"Set-LocalUser -Name '{name}' -Description '{description}'")
                
                for update_cmd in updates:
                    result = await self.connection.run(update_cmd, shell=True)
                    if result.rc == 0:
                        changed = True
            
            # Handle groups
            if groups:
                if isinstance(groups, str):
                    groups = [groups]
                
                for group in groups:
                    if groups_action == "add" or groups_action == "replace":
                        add_cmd = f"Add-LocalGroupMember -Group '{group}' -Member '{name}' -ErrorAction SilentlyContinue"
                        result = await self.connection.run(add_cmd, shell=True)
                        if result.rc == 0:
                            changed = True
                    elif groups_action == "remove":
                        remove_cmd = f"Remove-LocalGroupMember -Group '{group}' -Member '{name}' -ErrorAction SilentlyContinue"
                        result = await self.connection.run(remove_cmd, shell=True)
                        if result.rc == 0:
                            changed = True
            
            # Handle account settings
            if account_disabled:
                result = await self.connection.run(f"Disable-LocalUser -Name '{name}'", shell=True)
            else:
                result = await self.connection.run(f"Enable-LocalUser -Name '{name}'", shell=True)
        
        return ModuleResult(
            changed=changed,
            msg=f"User {name} {'created' if not user_exists and state == 'present' else 'removed' if state == 'absent' and user_exists else 'updated' if changed else 'unchanged'}",
            results={"name": name, "state": state},
        )
