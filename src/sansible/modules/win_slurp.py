"""
Sansible win_slurp module

Read file contents from Windows hosts.
"""

import base64
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WinSlurpModule(Module):
    """
    Fetch a file from a Windows node and return its content base64-encoded.
    """
    
    name = "win_slurp"
    required_args = ["src"]
    optional_args = {}
    
    async def run(self) -> ModuleResult:
        """Read file and return base64-encoded content."""
        src = self.args["src"]
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Check if file exists
        check_cmd = f"Test-Path -Path '{src}' -PathType Leaf"
        result = await self.connection.run(check_cmd, shell=True)
        if 'True' not in result.stdout:
            return ModuleResult(
                failed=True,
                msg=f"File not found: {src}",
            )
        
        # Read file content and encode as base64
        read_cmd = f"[Convert]::ToBase64String([System.IO.File]::ReadAllBytes('{src}'))"
        result = await self.connection.run(read_cmd, shell=True)
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to read file: {result.stderr}",
            )
        
        content_b64 = result.stdout.strip()
        
        return ModuleResult(
            changed=False,
            msg=f"Slurped {src}",
            results={
                "content": content_b64,
                "encoding": "base64",
                "source": src,
            },
        )
