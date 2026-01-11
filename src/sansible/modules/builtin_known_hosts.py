"""
Sansible known_hosts module

Manage SSH known_hosts file entries.
"""

import os
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class KnownHostsModule(Module):
    """
    Add or remove SSH host keys from known_hosts file.
    """
    
    name = "known_hosts"
    required_args = ["name"]
    optional_args = {
        "key": None,
        "path": None,  # Default: ~/.ssh/known_hosts
        "state": "present",  # present or absent
        "hash_host": False,
    }
    
    async def run(self) -> ModuleResult:
        """Manage known_hosts entry."""
        name = self.args["name"]  # Host name
        key = self.get_arg("key")
        path = self.get_arg("path")
        state = self.get_arg("state", "present")
        hash_host = self.get_arg("hash_host", False)
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Default path
        if not path:
            result = await self.connection.run("echo ~/.ssh/known_hosts", shell=True)
            path = result.stdout.strip()
        
        if state == "present" and not key:
            # Need to fetch the key
            if self.context.check_mode:
                return ModuleResult(
                    changed=True,
                    msg=f"Would add {name} to {path} (key would be fetched)",
                )
            
            result = await self.connection.run(f"ssh-keyscan -H '{name}' 2>/dev/null", shell=True)
            if result.rc != 0 or not result.stdout.strip():
                return ModuleResult(
                    failed=True,
                    msg=f"Failed to fetch SSH key for {name}",
                )
            key = result.stdout.strip()
        
        # Read current known_hosts
        result = await self.connection.run(f"cat '{path}' 2>/dev/null || true", shell=True)
        current_content = result.stdout
        lines = current_content.splitlines()
        
        # Check if host is already present
        host_present = False
        host_line_idx = None
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('#'):
                parts = line.split()
                if parts:
                    # Host can be comma-separated list
                    hosts = parts[0].split(',')
                    if name in hosts or f"[{name}]" in parts[0]:
                        host_present = True
                        host_line_idx = i
                        break
        
        changed = False
        
        if state == "absent":
            if host_present and host_line_idx is not None:
                del lines[host_line_idx]
                changed = True
        else:  # state == "present"
            if not host_present:
                lines.append(key)
                changed = True
        
        if self.context.check_mode:
            return ModuleResult(
                changed=changed,
                msg=f"Would {'add' if state == 'present' else 'remove'} {name} {'to' if state == 'present' else 'from'} {path}",
            )
        
        if changed:
            # Ensure directory exists
            dir_path = os.path.dirname(path)
            await self.connection.run(f"mkdir -p '{dir_path}'", shell=True)
            
            # Write updated content
            new_content = '\n'.join(lines)
            if not new_content.endswith('\n') and new_content:
                new_content += '\n'
            
            escaped = new_content.replace("'", "'\"'\"'")
            result = await self.connection.run(f"printf '%s' '{escaped}' > '{path}'", shell=True)
            if result.rc != 0:
                return ModuleResult(
                    failed=True,
                    msg=f"Failed to write known_hosts: {result.stderr}",
                )
        
        return ModuleResult(
            changed=changed,
            msg=f"Host {name} {'added to' if state == 'present' and changed else 'removed from' if state == 'absent' and changed else 'already in'} {path}",
            results={"name": name, "path": path},
        )
