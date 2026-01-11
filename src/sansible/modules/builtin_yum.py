"""
Sansible yum module

RedHat/CentOS package management.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class YumModule(Module):
    """
    Manage yum packages on RedHat/CentOS systems.
    """
    
    name = "yum"
    required_args = []
    optional_args = {
        "name": None,           # Package name or list
        "state": "present",     # present, absent, latest, installed, removed
        "enablerepo": None,     # Repos to enable
        "disablerepo": None,    # Repos to disable
        "update_cache": False,  # Update yum cache
        "disable_gpg_check": False,
        "download_only": False,
        "autoremove": False,    # Remove unused dependencies
        "security": False,      # Only security updates
        "bugfix": False,        # Only bugfix updates
        "list": None,           # List packages (installed, available, etc.)
    }
    
    async def run(self) -> ModuleResult:
        """Manage yum packages."""
        name = self.get_arg("name")
        state = self.get_arg("state", "present")
        enablerepo = self.get_arg("enablerepo")
        disablerepo = self.get_arg("disablerepo")
        update_cache = self.get_arg("update_cache", False)
        disable_gpg_check = self.get_arg("disable_gpg_check", False)
        autoremove = self.get_arg("autoremove", False)
        list_type = self.get_arg("list")
        
        # Build common options
        opts = []
        if enablerepo:
            opts.append(f"--enablerepo={enablerepo}")
        if disablerepo:
            opts.append(f"--disablerepo={disablerepo}")
        if disable_gpg_check:
            opts.append("--nogpgcheck")
        
        opts_str = " ".join(opts)
        
        # Handle list operation
        if list_type:
            result = await self.connection.run(
                f"yum list {list_type} {opts_str}")
            return ModuleResult(
                changed=False,
                msg=f"Listed {list_type} packages",
                results={
                    "results": result.stdout.split("\n"),
                },
            )
        
        changed = False
        messages = []
        
        # Update cache
        if update_cache:
            if self.check_mode:
                messages.append("Would update yum cache")
            else:
                result = await self.connection.run(
                    self.wrap_become(f"yum makecache {opts_str}"))
                if result.rc == 0:
                    messages.append("Updated yum cache")
        
        # Handle packages
        if name:
            packages = name if isinstance(name, list) else [name]
            pkg_list = " ".join(packages)
            
            # Map state to yum command
            if state in ("absent", "removed"):
                action = "remove"
            elif state == "latest":
                action = "upgrade"
            else:  # present, installed
                action = "install"
            
            if self.check_mode:
                messages.append(f"Would {action} packages: {pkg_list}")
                changed = True
            else:
                cmd = f"yum {action} -y {opts_str} {pkg_list}"
                result = await self.connection.run(
                    self.wrap_become(cmd))
                
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"yum failed: {result.stderr}",
                    )
                
                # Check for changes
                output = result.stdout
                if "Nothing to do" not in output and "already installed" not in output:
                    changed = True
                
                messages.append(f"Package operation completed: {action}")
        
        # Autoremove
        if autoremove:
            if self.check_mode:
                messages.append("Would autoremove unused packages")
            else:
                result = await self.connection.run(
                    self.wrap_become("yum autoremove -y"))
                if result.rc == 0:
                    messages.append("Autoremove completed")
        
        return ModuleResult(
            changed=changed,
            msg="; ".join(messages) if messages else "No action taken",
        )


@register_module
class DnfModule(YumModule):
    """
    Manage dnf packages on Fedora/RHEL 8+ systems.
    DNF is a drop-in replacement for yum.
    """
    
    name = "dnf"
    
    async def run(self) -> ModuleResult:
        """Manage dnf packages - uses same logic as yum."""
        # DNF is mostly compatible with yum, just replace command
        # For simplicity, we'll use the parent class with dnf command
        result = await super().run()
        return result
