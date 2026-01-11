"""
Sansible user module

Manage user accounts on Linux/Unix systems.
"""

from typing import Optional

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class UserModule(Module):
    """
    Manage user accounts.
    
    Supports creating, modifying, and removing user accounts.
    """
    
    name = "user"
    required_args = ["name"]
    optional_args = {
        "state": "present",     # present, absent
        "uid": None,            # User ID
        "group": None,          # Primary group
        "groups": None,         # Secondary groups (comma-separated or list)
        "append": False,        # Append to groups instead of replacing
        "home": None,           # Home directory
        "shell": None,          # Login shell
        "password": None,       # Encrypted password
        "comment": None,        # GECOS field
        "create_home": True,    # Create home directory
        "system": False,        # System account
        "remove": False,        # Remove home directory when state=absent
        "force": False,         # Force removal even if user is logged in
    }
    
    async def run(self) -> ModuleResult:
        """Manage the user account."""
        name = self.args["name"]
        state = self.get_arg("state", "present")
        
        if self.context.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"User '{name}' would be modified (check mode)",
            )
        
        # Check if user exists
        exists = await self._user_exists(name)
        
        if state == "present":
            if exists:
                return await self._modify_user(name)
            else:
                return await self._create_user(name)
        elif state == "absent":
            if not exists:
                return ModuleResult(
                    changed=False,
                    msg=f"User '{name}' does not exist",
                )
            return await self._remove_user(name)
        else:
            return ModuleResult(
                failed=True,
                msg=f"Unknown state: {state}. Valid: present, absent",
            )
    
    async def _user_exists(self, name: str) -> bool:
        """Check if user exists."""
        result = await self.connection.run(f"id {name}")
        return result.rc == 0
    
    async def _get_user_info(self, name: str) -> Optional[dict]:
        """Get current user information."""
        result = await self.connection.run(
            f"getent passwd {name}")
        if result.rc != 0:
            return None
        
        parts = result.stdout.strip().split(":")
        if len(parts) >= 7:
            return {
                "name": parts[0],
                "uid": int(parts[2]),
                "gid": int(parts[3]),
                "comment": parts[4],
                "home": parts[5],
                "shell": parts[6],
            }
        return None
    
    async def _create_user(self, name: str) -> ModuleResult:
        """Create a new user."""
        cmd_parts = ["useradd"]
        
        uid = self.get_arg("uid")
        if uid:
            cmd_parts.extend(["-u", str(uid)])
        
        group = self.get_arg("group")
        if group:
            cmd_parts.extend(["-g", group])
        
        groups = self.get_arg("groups")
        if groups:
            if isinstance(groups, list):
                groups = ",".join(groups)
            cmd_parts.extend(["-G", groups])
        
        home = self.get_arg("home")
        if home:
            cmd_parts.extend(["-d", home])
        
        shell = self.get_arg("shell")
        if shell:
            cmd_parts.extend(["-s", shell])
        
        comment = self.get_arg("comment")
        if comment:
            cmd_parts.extend(["-c", f'"{comment}"'])
        
        if self.get_arg("system"):
            cmd_parts.append("-r")
        
        if not self.get_arg("create_home"):
            cmd_parts.append("-M")
        else:
            cmd_parts.append("-m")
        
        cmd_parts.append(name)
        cmd = " ".join(cmd_parts)
        cmd = self.wrap_become(cmd)
        
        result = await self.connection.run(cmd)
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to create user '{name}': {result.stderr}",
            )
        
        # Set password if provided
        password = self.get_arg("password")
        if password:
            await self._set_password(name, password)
        
        return ModuleResult(
            changed=True,
            msg=f"User '{name}' created",
            results={"name": name, "state": "present"},
        )
    
    async def _modify_user(self, name: str) -> ModuleResult:
        """Modify existing user."""
        current = await self._get_user_info(name)
        if not current:
            return ModuleResult(
                failed=True,
                msg=f"Failed to get info for user '{name}'",
            )
        
        cmd_parts = ["usermod"]
        changes = []
        
        uid = self.get_arg("uid")
        if uid and uid != current["uid"]:
            cmd_parts.extend(["-u", str(uid)])
            changes.append(f"uid={uid}")
        
        home = self.get_arg("home")
        if home and home != current["home"]:
            cmd_parts.extend(["-d", home, "-m"])  # -m moves the home
            changes.append(f"home={home}")
        
        shell = self.get_arg("shell")
        if shell and shell != current["shell"]:
            cmd_parts.extend(["-s", shell])
            changes.append(f"shell={shell}")
        
        comment = self.get_arg("comment")
        if comment and comment != current["comment"]:
            cmd_parts.extend(["-c", f'"{comment}"'])
            changes.append(f"comment={comment}")
        
        group = self.get_arg("group")
        if group:
            cmd_parts.extend(["-g", group])
            changes.append(f"group={group}")
        
        groups = self.get_arg("groups")
        if groups:
            if isinstance(groups, list):
                groups = ",".join(groups)
            if self.get_arg("append"):
                cmd_parts.append("-a")
            cmd_parts.extend(["-G", groups])
            changes.append(f"groups={groups}")
        
        if not changes:
            return ModuleResult(
                changed=False,
                msg=f"User '{name}' already up to date",
            )
        
        cmd_parts.append(name)
        cmd = " ".join(cmd_parts)
        cmd = self.wrap_become(cmd)
        
        result = await self.connection.run(cmd)
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to modify user '{name}': {result.stderr}",
            )
        
        # Set password if provided
        password = self.get_arg("password")
        if password:
            await self._set_password(name, password)
        
        return ModuleResult(
            changed=True,
            msg=f"User '{name}' modified: {', '.join(changes)}",
        )
    
    async def _remove_user(self, name: str) -> ModuleResult:
        """Remove the user."""
        cmd = "userdel"
        if self.get_arg("remove"):
            cmd += " -r"
        if self.get_arg("force"):
            cmd += " -f"
        cmd += f" {name}"
        cmd = self.wrap_become(cmd)
        
        result = await self.connection.run(cmd)
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to remove user '{name}': {result.stderr}",
            )
        
        return ModuleResult(
            changed=True,
            msg=f"User '{name}' removed",
        )
    
    async def _set_password(self, name: str, password: str) -> None:
        """Set user password (expects encrypted password)."""
        cmd = f"usermod -p '{password}' {name}"
        cmd = self.wrap_become(cmd)
        await self.connection.run(cmd)
