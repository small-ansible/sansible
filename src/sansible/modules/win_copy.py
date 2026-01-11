"""
Sansible win_copy module

Copy files to Windows hosts.
"""

from pathlib import Path
from typing import Optional

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WinCopyModule(Module):
    """
    Copy files from the control node to Windows hosts.
    
    Uses chunked base64 transfer over WinRM for reliable file copying.
    """
    
    name = "win_copy"
    required_args = []  # Either src or content is required
    optional_args = {
        "dest": None,
        "src": None,
        "content": None,
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
        """Copy the file to Windows host."""
        dest = self.args["dest"]
        src = self.get_arg("src")
        content = self.get_arg("content")
        force = self.get_arg("force", True)
        remote_src = self.get_arg("remote_src", False)
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Normalize Windows path
        dest = dest.replace('/', '\\')
        
        # Handle content-based copy
        if content is not None:
            return await self._copy_content(content, dest)
        
        # Handle remote_src (copy within Windows)
        if remote_src:
            return await self._copy_remote(src, dest)
        
        # Handle file copy from control node
        return await self._copy_file(src, dest, force)
    
    async def _copy_content(self, content: str, dest: str) -> ModuleResult:
        """Copy inline content to Windows destination."""
        import tempfile
        
        # Write content to temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.tmp') as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            # Check if destination exists and has same content
            remote_stat = await self.connection.stat(dest)
            if remote_stat and remote_stat.get("exists"):
                local_size = len(content.encode('utf-8'))
                if remote_stat.get("size") == local_size:
                    return ModuleResult(
                        changed=False,
                        msg="Content already matches",
                    )
            
            # Upload the file
            await self.connection.put(temp_path, dest)
            
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
        force: bool,
    ) -> ModuleResult:
        """Copy a file from control node to Windows target."""
        src_path = Path(src)
        
        if not src_path.exists():
            return ModuleResult(
                failed=True,
                msg=f"Source file not found: {src}",
            )
        
        if src_path.is_dir():
            return ModuleResult(
                failed=True,
                msg="Directory copy not yet implemented for Windows",
            )
        
        # Check if we need to copy
        if not force:
            remote_stat = await self.connection.stat(dest)
            if remote_stat and remote_stat.get("exists"):
                local_size = src_path.stat().st_size
                if remote_stat.get("size") == local_size:
                    return ModuleResult(
                        changed=False,
                        msg="File already exists with same size",
                        results={"dest": dest, "src": src},
                    )
        
        # Upload the file
        await self.connection.put(src_path, dest)
        
        return ModuleResult(
            changed=True,
            msg=f"Copied {src} to {dest}",
            results={
                "dest": dest,
                "src": src,
                "size": src_path.stat().st_size,
            },
        )
    
    async def _copy_remote(self, src: str, dest: str) -> ModuleResult:
        """Copy a file within the Windows host."""
        src = src.replace('/', '\\')
        dest = dest.replace('/', '\\')
        
        # Use PowerShell Copy-Item
        result = await self.connection.run(
            f"Copy-Item -Path '{src}' -Destination '{dest}' -Force",
            shell=True
        )
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                rc=result.rc,
                stdout=result.stdout,
                stderr=result.stderr,
                msg=f"Remote copy failed: {result.stderr}",
            )
        
        return ModuleResult(
            changed=True,
            msg=f"Copied {src} to {dest} (remote)",
            results={"dest": dest, "src": src},
        )
