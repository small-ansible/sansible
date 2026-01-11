"""
Sansible cron module

Manage crontab entries.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class CronModule(Module):
    """
    Manage crontab entries for periodic job scheduling.
    """
    
    name = "cron"
    required_args = ["name"]
    optional_args = {
        "job": None,
        "minute": "*",
        "hour": "*",
        "day": "*",
        "month": "*",
        "weekday": "*",
        "user": None,
        "state": "present",
        "disabled": False,
        "special_time": None,  # reboot, hourly, daily, weekly, monthly, yearly, annually
        "cron_file": None,
        "env": False,  # If true, manages environment variable
        "value": None,  # For env=true
        "insertafter": None,
        "insertbefore": None,
        "backup": False,
    }
    
    async def run(self) -> ModuleResult:
        """Manage cron entry."""
        name = self.args["name"]
        job = self.get_arg("job")
        minute = self.get_arg("minute", "*")
        hour = self.get_arg("hour", "*")
        day = self.get_arg("day", "*")
        month = self.get_arg("month", "*")
        weekday = self.get_arg("weekday", "*")
        user = self.get_arg("user")
        state = self.get_arg("state", "present")
        disabled = self.get_arg("disabled", False)
        special_time = self.get_arg("special_time")
        is_env = self.get_arg("env", False)
        env_value = self.get_arg("value")
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        if state == "present" and not is_env and not job:
            return ModuleResult(
                failed=True,
                msg="job is required when state=present",
            )
        
        if is_env and state == "present" and env_value is None:
            return ModuleResult(
                failed=True,
                msg="value is required when env=true and state=present",
            )
        
        # Get current crontab
        crontab_cmd = "crontab -l 2>/dev/null || true"
        if user:
            crontab_cmd = f"crontab -u '{user}' -l 2>/dev/null || true"
        
        result = await self.connection.run(crontab_cmd, shell=True)
        current_crontab = result.stdout if result.rc == 0 else ""
        lines = current_crontab.splitlines()
        
        # Build the cron entry identifier comment
        identifier = f"#Ansible: {name}"
        
        # Find existing entry
        entry_idx = None
        for i, line in enumerate(lines):
            if line.strip() == identifier:
                entry_idx = i
                break
        
        changed = False
        new_lines = lines.copy()
        
        if is_env:
            # Handle environment variable
            new_entry = f"{name}={env_value}" if state == "present" else None
        else:
            # Build cron schedule
            if special_time:
                special_map = {
                    "reboot": "@reboot",
                    "hourly": "@hourly",
                    "daily": "@daily",
                    "weekly": "@weekly",
                    "monthly": "@monthly",
                    "yearly": "@yearly",
                    "annually": "@annually",
                }
                schedule = special_map.get(special_time, f"@{special_time}")
            else:
                schedule = f"{minute} {hour} {day} {month} {weekday}"
            
            if disabled:
                new_entry = f"#{schedule} {job}" if state == "present" else None
            else:
                new_entry = f"{schedule} {job}" if state == "present" else None
        
        if state == "absent":
            if entry_idx is not None:
                # Remove the identifier and the following entry
                del new_lines[entry_idx]
                if entry_idx < len(new_lines):
                    del new_lines[entry_idx]
                changed = True
        else:
            if entry_idx is not None:
                # Update existing entry
                current_entry = new_lines[entry_idx + 1] if entry_idx + 1 < len(new_lines) else ""
                if current_entry != new_entry:
                    new_lines[entry_idx + 1] = new_entry
                    changed = True
            else:
                # Add new entry
                new_lines.append(identifier)
                new_lines.append(new_entry)
                changed = True
        
        if self.context.check_mode:
            return ModuleResult(
                changed=changed,
                msg=f"Cron entry would be {'updated' if changed else 'unchanged'}",
            )
        
        if changed:
            # Write new crontab
            new_crontab = "\n".join(new_lines)
            if not new_crontab.endswith("\n"):
                new_crontab += "\n"
            
            # Escape for shell
            escaped = new_crontab.replace("'", "'\"'\"'")
            
            crontab_install_cmd = f"echo '{escaped}' | crontab -"
            if user:
                crontab_install_cmd = f"echo '{escaped}' | crontab -u '{user}' -"
            
            result = await self.connection.run(crontab_install_cmd, shell=True)
            if result.rc != 0:
                return ModuleResult(
                    failed=True,
                    msg=f"Failed to update crontab: {result.stderr}",
                )
        
        return ModuleResult(
            changed=changed,
            msg=f"Cron entry for '{name}' {'updated' if changed else 'unchanged'}",
            results={"name": name, "state": state},
        )
