"""
Sansible file module

Manage file and directory attributes.
"""

import os
from pathlib import Path
from typing import Optional

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class FileModule(Module):
    """
    Manage files and directories.
    
    Supports:
    - Creating directories (state: directory)
    - Creating empty files (state: touch)
    - Deleting files/directories (state: absent)
    - Checking existence (state: file)
    - Setting mode/permissions
    """
    
    name = "file"
    required_args = ["path"]
    optional_args = {
        "state": "file",  # file, directory, absent, touch, link
        "mode": None,
        "owner": None,  # Not fully implemented
        "group": None,  # Not fully implemented
        "recurse": False,
        "force": False,
        "follow": True,
        "src": None,  # For symlinks
    }
    
    async def run(self) -> ModuleResult:
        """Execute the file operation."""
        path = self.args["path"]
        state = self.get_arg("state", "file")
        mode = self.get_arg("mode")
        recurse = self.get_arg("recurse", False)
        force = self.get_arg("force", False)
        src = self.get_arg("src")
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Check mode - report what would happen without making changes
        if self.context.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"Path would be set to state={state} (check mode)",
                results={"path": path, "state": state},
            )
        
        if state == "absent":
            return await self._ensure_absent(path)
        elif state == "directory":
            return await self._ensure_directory(path, mode, recurse)
        elif state == "touch":
            return await self._ensure_touch(path, mode)
        elif state == "file":
            return await self._ensure_file(path, mode)
        elif state == "link":
            return await self._ensure_link(path, src, force)
        else:
            return ModuleResult(
                failed=True,
                msg=f"Unknown state: {state}. Supported: file, directory, absent, touch, link",
            )
    
    async def _ensure_absent(self, path: str) -> ModuleResult:
        """Ensure file/directory is absent."""
        stat = await self.connection.stat(path)
        
        if not stat or not stat.get("exists"):
            return ModuleResult(
                changed=False,
                msg=f"Path does not exist: {path}",
                results={"path": path, "state": "absent"},
            )
        
        # Remove file or directory
        if stat.get("isdir"):
            # Use rm -rf for directories on Unix
            result = await self.connection.run(f'rm -rf "{path}"')
        else:
            result = await self.connection.run(f'rm -f "{path}"')
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to remove {path}: {result.stderr}",
                rc=result.rc,
                stderr=result.stderr,
            )
        
        return ModuleResult(
            changed=True,
            msg=f"Removed: {path}",
            results={"path": path, "state": "absent"},
        )
    
    async def _ensure_directory(
        self, 
        path: str, 
        mode: Optional[str],
        recurse: bool,
    ) -> ModuleResult:
        """Ensure directory exists."""
        stat = await self.connection.stat(path)
        
        if stat and stat.get("exists"):
            if stat.get("isdir"):
                # Already a directory
                # TODO: Check/set mode if specified
                return ModuleResult(
                    changed=False,
                    msg=f"Directory already exists: {path}",
                    results={"path": path, "state": "directory"},
                )
            else:
                return ModuleResult(
                    failed=True,
                    msg=f"Path exists but is not a directory: {path}",
                )
        
        # Create directory
        await self.connection.mkdir(path, mode=mode)
        
        return ModuleResult(
            changed=True,
            msg=f"Created directory: {path}",
            results={"path": path, "state": "directory"},
        )
    
    async def _ensure_touch(self, path: str, mode: Optional[str]) -> ModuleResult:
        """Create empty file or update timestamp."""
        stat = await self.connection.stat(path)
        
        if stat and stat.get("exists") and stat.get("isdir"):
            return ModuleResult(
                failed=True,
                msg=f"Path is a directory, cannot touch: {path}",
            )
        
        # Touch the file
        result = await self.connection.run(f'touch "{path}"')
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to touch {path}: {result.stderr}",
                rc=result.rc,
                stderr=result.stderr,
            )
        
        # Set mode if specified
        if mode:
            chmod_result = await self.connection.run(f'chmod {mode} "{path}"')
            if chmod_result.rc != 0:
                return ModuleResult(
                    failed=True,
                    msg=f"Failed to set mode on {path}: {chmod_result.stderr}",
                )
        
        changed = not (stat and stat.get("exists"))
        return ModuleResult(
            changed=changed,
            msg=f"{'Created' if changed else 'Touched'}: {path}",
            results={"path": path, "state": "touch"},
        )
    
    async def _ensure_file(self, path: str, mode: Optional[str]) -> ModuleResult:
        """Ensure path exists and is a file."""
        stat = await self.connection.stat(path)
        
        if not stat or not stat.get("exists"):
            return ModuleResult(
                failed=True,
                msg=f"Path does not exist: {path}",
            )
        
        if stat.get("isdir"):
            return ModuleResult(
                failed=True,
                msg=f"Path is a directory, not a file: {path}",
            )
        
        # File exists - TODO: check/set mode
        return ModuleResult(
            changed=False,
            msg=f"File exists: {path}",
            results={"path": path, "state": "file"},
        )
    
    async def _ensure_link(
        self, 
        path: str, 
        src: Optional[str], 
        force: bool,
    ) -> ModuleResult:
        """Create a symbolic link."""
        if not src:
            return ModuleResult(
                failed=True,
                msg="'src' is required when state=link",
            )
        
        stat = await self.connection.stat(path)
        
        if stat and stat.get("exists"):
            if force:
                # Remove existing
                result = await self.connection.run(f'rm -f "{path}"')
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"Failed to remove existing {path}: {result.stderr}",
                    )
            else:
                return ModuleResult(
                    changed=False,
                    msg=f"Path already exists: {path}",
                    results={"path": path, "src": src, "state": "link"},
                )
        
        # Create symlink
        result = await self.connection.run(f'ln -s "{src}" "{path}"')
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to create symlink: {result.stderr}",
                rc=result.rc,
                stderr=result.stderr,
            )
        
        return ModuleResult(
            changed=True,
            msg=f"Created link: {path} -> {src}",
            results={"path": path, "src": src, "state": "link"},
        )
