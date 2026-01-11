"""
Sansible script module

Run a local script on a remote node.
"""

import base64
import os
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class ScriptModule(Module):
    """
    Transfer a local script to a remote node and execute it.
    
    The script is copied to a temp location on the remote, executed,
    and then removed.
    """
    
    name = "script"
    required_args = ["_raw_params"]  # Script path with optional args
    optional_args = {
        "chdir": None,
        "creates": None,
        "removes": None,
        "executable": None,
    }
    
    async def run(self) -> ModuleResult:
        """Run local script on remote node."""
        raw_params = self.args.get("_raw_params", "")
        chdir = self.get_arg("chdir")
        creates = self.get_arg("creates")
        removes = self.get_arg("removes")
        executable = self.get_arg("executable")
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Parse raw_params to get script path and args
        parts = raw_params.split()
        if not parts:
            return ModuleResult(
                failed=True,
                msg="No script specified",
            )
        
        script_path = parts[0]
        script_args = " ".join(parts[1:]) if len(parts) > 1 else ""
        
        # Handle creates/removes checks
        if creates:
            stat_result = await self.connection.stat(creates)
            if stat_result and stat_result.get("exists", False):
                return ModuleResult(
                    changed=False,
                    msg=f"Skipped - {creates} exists",
                )
        
        if removes:
            stat_result = await self.connection.stat(removes)
            if not stat_result or not stat_result.get("exists", False):
                return ModuleResult(
                    changed=False,
                    msg=f"Skipped - {removes} does not exist",
                )
        
        # Read local script content - check both context attribute and vars
        playbook_dir = None
        if hasattr(self.context, 'playbook_dir') and self.context.playbook_dir:
            playbook_dir = self.context.playbook_dir
        elif hasattr(self.context, 'vars') and self.context.vars.get('playbook_dir'):
            playbook_dir = self.context.vars.get('playbook_dir')
        
        if not os.path.isabs(script_path) and playbook_dir:
            full_path = os.path.join(playbook_dir, script_path)
            if os.path.exists(full_path):
                script_path = full_path
        
        if not os.path.exists(script_path):
            return ModuleResult(
                failed=True,
                msg=f"Script not found: {script_path}",
            )
        
        with open(script_path, 'r') as f:
            script_content = f.read()
        
        if self.context.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"Would run script: {script_path}",
            )
        
        # Create temp file on remote
        result = await self.connection.run("mktemp", shell=True)
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to create temp file: {result.stderr}",
            )
        
        remote_script = result.stdout.strip()
        
        try:
            # Transfer script content using base64 to handle special chars
            script_b64 = base64.b64encode(script_content.encode()).decode()
            transfer_cmd = f"echo '{script_b64}' | base64 -d > '{remote_script}'"
            
            result = await self.connection.run(transfer_cmd, shell=True)
            if result.rc != 0:
                return ModuleResult(
                    failed=True,
                    msg=f"Failed to transfer script: {result.stderr}",
                )
            
            # Make executable
            result = await self.connection.run(f"chmod +x '{remote_script}'", shell=True)
            if result.rc != 0:
                return ModuleResult(
                    failed=True,
                    msg=f"Failed to make script executable: {result.stderr}",
                )
            
            # Build execution command
            if executable:
                exec_cmd = f"'{executable}' '{remote_script}'"
            else:
                exec_cmd = f"'{remote_script}'"
            
            if script_args:
                exec_cmd += f" {script_args}"
            
            if chdir:
                exec_cmd = f"cd '{chdir}' && {exec_cmd}"
            
            # Execute
            result = await self.connection.run(exec_cmd, shell=True)
            
            return ModuleResult(
                changed=True,
                msg="Script executed",
                results={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "rc": result.rc,
                },
                failed=result.rc != 0,
            )
        finally:
            # Cleanup temp script
            await self.connection.run(f"rm -f '{remote_script}'", shell=True)
