"""
Sansible tempfile module

Create temporary files and directories.
"""

import os
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class TempfileModule(Module):
    """
    Create a temporary file or directory.
    
    Returns path to created temp file/directory.
    """
    
    name = "tempfile"
    required_args = []
    optional_args = {
        "state": "file",  # file or directory
        "prefix": "ansible.",
        "suffix": "",
        "path": None,  # parent directory
    }
    
    async def run(self) -> ModuleResult:
        """Create temporary file or directory."""
        state = self.get_arg("state", "file")
        prefix = self.get_arg("prefix", "ansible.")
        suffix = self.get_arg("suffix", "")
        path = self.get_arg("path")
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        if state not in ("file", "directory"):
            return ModuleResult(
                failed=True,
                msg=f"Invalid state: {state}. Must be 'file' or 'directory'",
            )
        
        if self.context.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"Would create temporary {state}",
            )
        
        # Build mktemp command
        if state == "directory":
            cmd = "mktemp -d"
        else:
            cmd = "mktemp"
        
        # Add template with prefix and suffix
        # mktemp template must have XXXXXX
        template = f"{prefix}XXXXXX{suffix}"
        
        if path:
            # Specify parent directory
            cmd = f"{cmd} -p '{path}' '{template}'"
        else:
            cmd = f"{cmd} -t '{template}'"
        
        result = await self.connection.run(cmd, shell=True)
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to create temporary {state}: {result.stderr}",
            )
        
        temp_path = result.stdout.strip()
        
        return ModuleResult(
            changed=True,
            msg=f"Created temporary {state}: {temp_path}",
            results={
                "path": temp_path,
                "state": state,
            },
        )
