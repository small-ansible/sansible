"""
Sansible package module

Generic OS package management.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class PackageModule(Module):
    """
    Generic OS package manager module.
    
    This module auto-detects the package manager and uses the appropriate
    tool (apt, yum, dnf, etc.) to manage packages.
    """
    
    name = "package"
    required_args = ["name"]
    optional_args = {
        "state": "present",     # present, absent, latest
        "use": None,            # Force specific package manager (apt, yum, dnf)
    }
    
    async def run(self) -> ModuleResult:
        """Manage packages."""
        name = self.args["name"]
        state = self.get_arg("state", "present")
        force_use = self.get_arg("use")
        
        # Handle list of packages
        if isinstance(name, list):
            packages = name
        else:
            packages = [p.strip() for p in name.split(",")]
        
        # Detect package manager
        pkg_manager = force_use or await self._detect_package_manager()
        
        if not pkg_manager:
            return ModuleResult(
                failed=True,
                msg="Could not detect package manager on this system",
            )
        
        # Check mode
        if self.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"Would {state} packages: {', '.join(packages)} using {pkg_manager}",
            )
        
        # Build command based on package manager and state
        if pkg_manager == "apt":
            result = await self._run_apt(packages, state)
        elif pkg_manager in ("yum", "dnf"):
            result = await self._run_yum_dnf(packages, state, pkg_manager)
        elif pkg_manager == "apk":
            result = await self._run_apk(packages, state)
        elif pkg_manager == "pacman":
            result = await self._run_pacman(packages, state)
        else:
            return ModuleResult(
                failed=True,
                msg=f"Unsupported package manager: {pkg_manager}",
            )
        
        return result
    
    async def _detect_package_manager(self) -> str | None:
        """Detect the OS package manager."""
        # Check for common package managers
        checks = [
            ("apt-get", "apt"),
            ("dnf", "dnf"),
            ("yum", "yum"),
            ("apk", "apk"),
            ("pacman", "pacman"),
        ]
        
        for cmd, name in checks:
            result = await self.connection.run(f"which {cmd}")
            if result.rc == 0:
                return name
        
        return None
    
    async def _run_apt(self, packages: list, state: str) -> ModuleResult:
        """Run apt package operations."""
        pkg_list = " ".join(packages)
        
        if state == "absent":
            cmd = f"apt-get remove -y {pkg_list}"
        elif state == "latest":
            cmd = f"apt-get update && apt-get install -y --only-upgrade {pkg_list}"
        else:  # present
            cmd = f"apt-get install -y {pkg_list}"
        
        result = await self.connection.run(self.wrap_become(cmd))
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"apt failed: {result.stderr}",
            )
        
        # Check if anything changed (look for "0 newly installed" etc.)
        changed = "0 newly installed" not in result.stdout and "is already the newest" not in result.stdout
        
        return ModuleResult(
            changed=changed,
            msg=f"Package operation completed",
            results={
                "packages": packages,
                "state": state,
            },
        )
    
    async def _run_yum_dnf(self, packages: list, state: str, manager: str) -> ModuleResult:
        """Run yum/dnf package operations."""
        pkg_list = " ".join(packages)
        
        if state == "absent":
            cmd = f"{manager} remove -y {pkg_list}"
        elif state == "latest":
            cmd = f"{manager} upgrade -y {pkg_list}"
        else:  # present
            cmd = f"{manager} install -y {pkg_list}"
        
        result = await self.connection.run(self.wrap_become(cmd))
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"{manager} failed: {result.stderr}",
            )
        
        changed = "Nothing to do" not in result.stdout and "already installed" not in result.stdout
        
        return ModuleResult(
            changed=changed,
            msg=f"Package operation completed",
            results={
                "packages": packages,
                "state": state,
            },
        )
    
    async def _run_apk(self, packages: list, state: str) -> ModuleResult:
        """Run apk package operations."""
        pkg_list = " ".join(packages)
        
        if state == "absent":
            cmd = f"apk del {pkg_list}"
        elif state == "latest":
            cmd = f"apk upgrade {pkg_list}"
        else:  # present
            cmd = f"apk add {pkg_list}"
        
        result = await self.connection.run(self.wrap_become(cmd))
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"apk failed: {result.stderr}",
            )
        
        return ModuleResult(
            changed=True,  # apk doesn't give clear "no change" output
            msg=f"Package operation completed",
            results={
                "packages": packages,
                "state": state,
            },
        )
    
    async def _run_pacman(self, packages: list, state: str) -> ModuleResult:
        """Run pacman package operations."""
        pkg_list = " ".join(packages)
        
        if state == "absent":
            cmd = f"pacman -R --noconfirm {pkg_list}"
        elif state == "latest":
            cmd = f"pacman -Syu --noconfirm {pkg_list}"
        else:  # present
            cmd = f"pacman -S --noconfirm --needed {pkg_list}"
        
        result = await self.connection.run(self.wrap_become(cmd))
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"pacman failed: {result.stderr}",
            )
        
        changed = "there is nothing to do" not in result.stdout.lower()
        
        return ModuleResult(
            changed=changed,
            msg=f"Package operation completed",
            results={
                "packages": packages,
                "state": state,
            },
        )
