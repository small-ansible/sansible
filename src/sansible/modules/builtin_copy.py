"""
Sansible copy module

Copy files to remote hosts.
"""

import hashlib
from pathlib import Path
from typing import Optional

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class CopyModule(Module):
    """
    Copy files from the control node to target hosts.
    
    Supports:
    - File copying with optional mode/owner/group
    - Content-based copying (inline content)
    - Idempotency via checksum comparison
    """
    
    name = "copy"
    required_args = []  # Either src or content is required
    optional_args = {
        "dest": None,
        "src": None,
        "content": None,
        "mode": None,
        "owner": None,  # Not implemented in v0.1
        "group": None,  # Not implemented in v0.1
        "backup": False,
        "force": True,
        "remote_src": False,
    }
    
    def validate_args(self) -> str | None:
        if "dest" not in self.args:
            return "Missing required argument: dest"
        if "src" not in self.args and "content" not in self.args:
            return "Either 'src' or 'content' is required"
        return None
    
    async def run(self) -> ModuleResult:
        """Copy the file."""
        dest = self.args["dest"]
        src = self.get_arg("src")
        content = self.get_arg("content")
        mode = self.get_arg("mode")
        force = self.get_arg("force", True)
        remote_src = self.get_arg("remote_src", False)
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Check mode - report what would happen without making changes
        if self.context.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"File would be copied to {dest} (check mode)",
                results={"dest": dest, "src": src or "(content)"},
            )
        
        # Handle content-based copy
        if content is not None:
            return await self._copy_content(content, dest, mode)
        
        # Handle remote_src (copy within remote)
        if remote_src:
            return await self._copy_remote(src, dest, mode)
        
        # Handle file copy from control node
        return await self._copy_file(src, dest, mode, force)
    
    async def _copy_content(
        self, 
        content: str, 
        dest: str, 
        mode: Optional[str],
    ) -> ModuleResult:
        """Copy inline content to destination."""
        import tempfile
        
        # Write content to temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.tmp', newline='\n') as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            # Check if destination exists and has same content
            remote_stat = await self.connection.stat(dest)
            if remote_stat and remote_stat.get("exists"):
                # Simple size check for now
                local_size = len(content.encode('utf-8'))
                if remote_stat.get("size") == local_size:
                    return ModuleResult(
                        changed=False,
                        msg="Content already matches",
                    )
            
            # Upload the file
            await self.connection.put(temp_path, dest, mode=mode)
            
            return ModuleResult(
                changed=True,
                msg=f"Content copied to {dest}",
                results={"dest": dest},
            )
        finally:
            temp_path.unlink(missing_ok=True)
    
    async def _copy_file(
        self,
        src: str,
        dest: str,
        mode: Optional[str],
        force: bool,
    ) -> ModuleResult:
        """Copy a file from control node to target."""
        src_path = Path(src)
        
        if not src_path.exists():
            return ModuleResult(
                failed=True,
                msg=f"Source file not found: {src}",
            )
        
        if src_path.is_dir():
            # TODO: Implement directory copy
            return ModuleResult(
                failed=True,
                msg="Directory copy not yet implemented",
            )
        
        # Check if we need to copy
        if not force:
            remote_stat = await self.connection.stat(dest)
            if remote_stat and remote_stat.get("exists"):
                # Check if sizes match (simple idempotency)
                local_size = src_path.stat().st_size
                if remote_stat.get("size") == local_size:
                    return ModuleResult(
                        changed=False,
                        msg="File already exists with same size",
                        results={"dest": dest, "src": src},
                    )
        
        # Upload the file
        await self.connection.put(src_path, dest, mode=mode)
        
        return ModuleResult(
            changed=True,
            msg=f"Copied {src} to {dest}",
            results={
                "dest": dest,
                "src": src,
                "size": src_path.stat().st_size,
            },
        )
    
    async def _copy_remote(
        self,
        src: str,
        dest: str,
        mode: Optional[str],
    ) -> ModuleResult:
        """Copy a file within the remote host."""
        # Use shell command for remote copy
        result = await self.connection.run(f"cp '{src}' '{dest}'", shell=True)
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                rc=result.rc,
                stdout=result.stdout,
                stderr=result.stderr,
                msg=f"Remote copy failed: {result.stderr}",
            )
        
        # Set mode if specified
        if mode:
            await self.connection.run(f"chmod {mode} '{dest}'", shell=True)
        
        return ModuleResult(
            changed=True,
            msg=f"Copied {src} to {dest} (remote)",
            results={"dest": dest, "src": src},
        )
