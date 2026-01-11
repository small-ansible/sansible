"""
Sansible slurp module

Read file contents and return them base64-encoded.
"""

import base64
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class SlurpModule(Module):
    """
    Fetch a file from a remote node and return its content base64-encoded.
    
    This is useful for fetching binary files or files with complex encoding.
    """
    
    name = "slurp"
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
        stat_result = await self.connection.stat(src)
        if not stat_result or not stat_result.get("exists", False):
            return ModuleResult(
                failed=True,
                msg=f"File not found: {src}",
            )
        
        # Check it's a file (not directory)
        if stat_result.get("isdir", False):
            return ModuleResult(
                failed=True,
                msg=f"Path is a directory, not a file: {src}",
            )
        
        # Read file content using base64 command on remote
        result = await self.connection.run(f"base64 '{src}'", shell=True)
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to read file: {result.stderr}",
            )
        
        # The remote base64 output may have newlines, clean it up
        content_b64 = result.stdout.replace('\n', '').replace('\r', '')
        
        return ModuleResult(
            changed=False,
            msg=f"Slurped {src}",
            results={
                "content": content_b64,
                "encoding": "base64",
                "source": src,
            },
        )
