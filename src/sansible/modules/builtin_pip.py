"""
Sansible pip module

Python package management via pip.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class PipModule(Module):
    """
    Manage Python packages with pip.
    """
    
    name = "pip"
    required_args = []  # Either name or requirements
    optional_args = {
        "name": None,           # Package name or list
        "state": "present",     # present, absent, latest, forcereinstall
        "requirements": None,   # Path to requirements.txt
        "virtualenv": None,     # Path to virtualenv
        "virtualenv_command": "virtualenv",
        "virtualenv_python": None,  # Python executable for venv
        "executable": None,     # Path to pip executable
        "extra_args": None,     # Extra arguments to pip
        "version": None,        # Specific version to install
        "editable": False,      # Install in editable mode
    }
    
    async def run(self) -> ModuleResult:
        """Manage pip packages."""
        name = self.get_arg("name")
        state = self.get_arg("state", "present")
        requirements = self.get_arg("requirements")
        virtualenv = self.get_arg("virtualenv")
        executable = self.get_arg("executable")
        extra_args = self.get_arg("extra_args", "")
        version = self.get_arg("version")
        editable = self.get_arg("editable", False)
        
        changed = False
        messages = []
        
        # Determine pip command
        if executable:
            pip_cmd = executable
        elif virtualenv:
            pip_cmd = f"{virtualenv}/bin/pip"
        else:
            pip_cmd = "pip3"
        
        # Create virtualenv if needed
        if virtualenv:
            # Check if venv exists
            result = await self.connection.run(f"test -d {virtualenv}")
            if result.rc != 0:
                if self.check_mode:
                    messages.append(f"Would create virtualenv: {virtualenv}")
                else:
                    venv_cmd = self.get_arg("virtualenv_command", "python3 -m venv")
                    venv_python = self.get_arg("virtualenv_python")
                    if venv_python:
                        venv_cmd = f"{venv_python} -m venv"
                    
                    result = await self.connection.run(
                        f"{venv_cmd} {virtualenv}")
                    if result.rc != 0:
                        return ModuleResult(
                            failed=True,
                            msg=f"Failed to create virtualenv: {result.stderr}",
                        )
                    messages.append(f"Created virtualenv: {virtualenv}")
                    changed = True
        
        # Install from requirements file
        if requirements:
            if self.check_mode:
                messages.append(f"Would install from requirements: {requirements}")
                changed = True
            else:
                cmd = f"{pip_cmd} install -r {requirements} {extra_args}"
                result = await self.connection.run(cmd)
                
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"pip install failed: {result.stderr}",
                    )
                
                if "Successfully installed" in result.stdout:
                    changed = True
                messages.append(f"Installed from requirements: {requirements}")
        
        # Handle named packages
        if name:
            packages = name if isinstance(name, list) else [name]
            
            for pkg in packages:
                # Add version if specified
                pkg_spec = pkg
                if version and "==" not in pkg and ">=" not in pkg:
                    pkg_spec = f"{pkg}=={version}"
                
                if self.check_mode:
                    messages.append(f"Would {state}: {pkg_spec}")
                    changed = True
                    continue
                
                if state == "absent":
                    cmd = f"{pip_cmd} uninstall -y {pkg} {extra_args}"
                elif state == "latest":
                    cmd = f"{pip_cmd} install --upgrade {pkg_spec} {extra_args}"
                elif state == "forcereinstall":
                    cmd = f"{pip_cmd} install --force-reinstall {pkg_spec} {extra_args}"
                else:  # present
                    if editable:
                        cmd = f"{pip_cmd} install -e {pkg_spec} {extra_args}"
                    else:
                        cmd = f"{pip_cmd} install {pkg_spec} {extra_args}"
                
                result = await self.connection.run(cmd)
                
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"pip failed for {pkg}: {result.stderr}",
                    )
                
                if "Successfully installed" in result.stdout or "Successfully uninstalled" in result.stdout:
                    changed = True
                elif "Requirement already satisfied" in result.stdout:
                    pass  # No change
                else:
                    changed = True
                
                messages.append(f"{state}: {pkg_spec}")
        
        return ModuleResult(
            changed=changed,
            msg="; ".join(messages) if messages else "No action taken",
        )
