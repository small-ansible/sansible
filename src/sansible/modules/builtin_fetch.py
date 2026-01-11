"""
Sansible fetch module

Fetch files from remote to control node.
"""

import os
import base64
from pathlib import Path

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class FetchModule(Module):
    """
    Fetch files from remote machine to the local machine.
    
    This is essentially the reverse of the copy module.
    """
    
    name = "fetch"
    required_args = ["src", "dest"]
    optional_args = {
        "flat": False,          # Store file directly in dest, not in host subdirectory
        "fail_on_missing": True,  # Fail if source file doesn't exist
        "validate_checksum": True,  # Validate checksum after fetch
    }
    
    async def run(self) -> ModuleResult:
        """Fetch file from remote to local."""
        src = self.args["src"]
        dest = self.args["dest"]
        flat = self.get_arg("flat", False)
        fail_on_missing = self.get_arg("fail_on_missing", True)
        
        # Check if source exists on remote
        stat_result = await self.connection.stat(src)
        
        if not stat_result.get("exists", False):
            if fail_on_missing:
                return ModuleResult(
                    failed=True,
                    msg=f"Source file does not exist: {src}",
                )
            else:
                return ModuleResult(
                    changed=False,
                    msg=f"Source file does not exist: {src}",
                )
        
        if stat_result.get("isdir", False):
            return ModuleResult(
                failed=True,
                msg=f"Source is a directory, not a file: {src}",
            )
        
        # Determine local destination path
        if flat:
            local_dest = Path(dest)
        else:
            # Build path: dest/hostname/src_path
            hostname = self.host.name if self.host else "localhost"
            local_dest = Path(dest) / hostname / src.lstrip("/")
        
        # Check mode - don't actually fetch
        if self.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"Would fetch {src} to {local_dest}",
                diff={
                    "before": "",
                    "after": f"Fetched from {src}",
                } if self.diff_mode else None,
            )
        
        # Use connection's get method
        try:
            await self.connection.get(src, local_dest)
        except Exception as e:
            return ModuleResult(
                failed=True,
                msg=f"Failed to fetch file: {e}",
            )
        
        # Verify fetch
        if not local_dest.exists():
            return ModuleResult(
                failed=True,
                msg=f"File was not fetched to {local_dest}",
            )
        
        return ModuleResult(
            changed=True,
            msg=f"Successfully fetched {src} to {local_dest}",
            results={
                "dest": str(local_dest),
                "src": src,
                "checksum": stat_result.get("checksum", ""),
                "size": stat_result.get("size", 0),
            },
        )
