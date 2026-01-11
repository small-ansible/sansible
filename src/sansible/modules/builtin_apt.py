"""
Sansible apt module

Debian/Ubuntu package management.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class AptModule(Module):
    """
    Manage apt packages on Debian/Ubuntu systems.
    """
    
    name = "apt"
    required_args = []  # Either "name" or "deb" or just "update_cache"
    optional_args = {
        "name": None,           # Package name or list
        "state": "present",     # present, absent, latest, build-dep, fixed
        "update_cache": False,  # Run apt-get update
        "cache_valid_time": 0,  # Cache validity in seconds
        "deb": None,            # Path to .deb file
        "dpkg_options": "force-confdef,force-confold",
        "autoremove": False,    # Remove unused dependencies
        "autoclean": False,     # Clean old packages
        "purge": False,         # Purge package configuration
        "install_recommends": None,  # Install recommended packages
        "force_apt_get": False,  # Use apt-get instead of apt
    }
    
    async def run(self) -> ModuleResult:
        """Manage apt packages."""
        name = self.get_arg("name")
        state = self.get_arg("state", "present")
        update_cache = self.get_arg("update_cache", False)
        deb = self.get_arg("deb")
        autoremove = self.get_arg("autoremove", False)
        autoclean = self.get_arg("autoclean", False)
        purge = self.get_arg("purge", False)
        
        changed = False
        messages = []
        
        # Update cache if requested
        if update_cache:
            if self.check_mode:
                messages.append("Would update apt cache")
            else:
                result = await self.connection.run(
                    self.wrap_become("apt-get update -qq"))
                if result.rc == 0:
                    messages.append("Updated apt cache")
                    changed = True
                else:
                    return ModuleResult(
                        failed=True,
                        msg=f"Failed to update apt cache: {result.stderr}",
                    )
        
        # Install .deb file
        if deb:
            if self.check_mode:
                messages.append(f"Would install {deb}")
            else:
                result = await self.connection.run(
                    self.wrap_become(f"dpkg -i {deb} || apt-get install -f -y"))
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"Failed to install deb: {result.stderr}",
                    )
                messages.append(f"Installed {deb}")
                changed = True
        
        # Handle packages
        if name:
            packages = name if isinstance(name, list) else [name]
            pkg_list = " ".join(packages)
            
            if self.check_mode:
                messages.append(f"Would {state} packages: {pkg_list}")
                changed = True
            else:
                if state == "absent":
                    flag = "--purge" if purge else ""
                    cmd = f"apt-get remove -y {flag} {pkg_list}"
                elif state == "latest":
                    cmd = f"apt-get install -y --only-upgrade {pkg_list}"
                elif state == "build-dep":
                    cmd = f"apt-get build-dep -y {pkg_list}"
                else:  # present
                    cmd = f"apt-get install -y {pkg_list}"
                
                result = await self.connection.run(
                    self.wrap_become(cmd))
                
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"apt-get failed: {result.stderr}",
                    )
                
                # Detect if anything changed
                output = result.stdout
                if "0 newly installed" not in output and "is already the newest" not in output:
                    changed = True
                
                messages.append(f"Package operation completed: {state}")
        
        # Autoremove
        if autoremove:
            if self.check_mode:
                messages.append("Would autoremove unused packages")
            else:
                result = await self.connection.run(
                    self.wrap_become("apt-get autoremove -y"))
                if result.rc == 0 and "0 to remove" not in result.stdout:
                    changed = True
                    messages.append("Removed unused packages")
        
        # Autoclean
        if autoclean:
            if self.check_mode:
                messages.append("Would clean package cache")
            else:
                await self.connection.run(
                    self.wrap_become("apt-get autoclean -y"))
                messages.append("Cleaned package cache")
        
        return ModuleResult(
            changed=changed,
            msg="; ".join(messages) if messages else "No action taken",
        )
