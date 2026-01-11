"""
Sansible win_file module

Manage files and directories on Windows hosts.
"""

from typing import Optional

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WinFileModule(Module):
    """
    Manage files and directories on Windows hosts.
    
    Supports:
    - Creating directories (state: directory)
    - Creating empty files (state: touch)
    - Deleting files/directories (state: absent)
    - Checking existence (state: file)
    """
    
    name = "win_file"
    required_args = ["path"]
    optional_args = {
        "state": "file",  # file, directory, absent, touch
        "force": False,
    }
    
    async def run(self) -> ModuleResult:
        """Execute the file operation on Windows."""
        path = self.args["path"]
        state = self.get_arg("state", "file")
        force = self.get_arg("force", False)
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        if state == "absent":
            return await self._ensure_absent(path, force)
        elif state == "directory":
            return await self._ensure_directory(path)
        elif state == "touch":
            return await self._ensure_touch(path)
        elif state == "file":
            return await self._ensure_file(path)
        else:
            return ModuleResult(
                failed=True,
                msg=f"Unknown state: {state}. Supported: file, directory, absent, touch",
            )
    
    async def _ensure_absent(self, path: str, force: bool) -> ModuleResult:
        """Ensure file/directory is absent on Windows."""
        # Check if path exists
        check_script = f'''
$path = "{path}"
if (Test-Path -LiteralPath $path) {{
    $item = Get-Item -LiteralPath $path -Force
    if ($item.PSIsContainer) {{
        Write-Output "directory"
    }} else {{
        Write-Output "file"
    }}
}} else {{
    Write-Output "absent"
}}
'''
        result = await self.connection.run(check_script)
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to check path: {result.stderr}",
                rc=result.rc,
            )
        
        current_state = result.stdout.strip()
        
        if current_state == "absent":
            return ModuleResult(
                changed=False,
                msg=f"Path does not exist: {path}",
                results={"path": path, "state": "absent"},
            )
        
        # Remove file or directory
        if current_state == "directory":
            remove_script = f'Remove-Item -LiteralPath "{path}" -Recurse -Force'
        else:
            remove_script = f'Remove-Item -LiteralPath "{path}" -Force'
        
        result = await self.connection.run(remove_script)
        
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
    
    async def _ensure_directory(self, path: str) -> ModuleResult:
        """Ensure directory exists on Windows."""
        script = f'''
$path = "{path}"
if (Test-Path -LiteralPath $path -PathType Container) {{
    Write-Output "exists"
}} elseif (Test-Path -LiteralPath $path) {{
    Write-Error "Path exists but is not a directory"
    exit 1
}} else {{
    New-Item -Path $path -ItemType Directory -Force | Out-Null
    Write-Output "created"
}}
'''
        result = await self.connection.run(script)
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to ensure directory: {result.stderr}",
                rc=result.rc,
                stderr=result.stderr,
            )
        
        changed = result.stdout.strip() == "created"
        return ModuleResult(
            changed=changed,
            msg=f"{'Created' if changed else 'Exists'}: {path}",
            results={"path": path, "state": "directory"},
        )
    
    async def _ensure_touch(self, path: str) -> ModuleResult:
        """Create empty file or update timestamp on Windows."""
        script = f'''
$path = "{path}"
$existed = Test-Path -LiteralPath $path
if (Test-Path -LiteralPath $path -PathType Container) {{
    Write-Error "Path is a directory"
    exit 1
}}
# Touch: create if not exists, update timestamp if exists
if (-not $existed) {{
    New-Item -Path $path -ItemType File -Force | Out-Null
    Write-Output "created"
}} else {{
    (Get-Item -LiteralPath $path).LastWriteTime = Get-Date
    Write-Output "touched"
}}
'''
        result = await self.connection.run(script)
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to touch {path}: {result.stderr}",
                rc=result.rc,
                stderr=result.stderr,
            )
        
        changed = result.stdout.strip() == "created"
        return ModuleResult(
            changed=changed,
            msg=f"{'Created' if changed else 'Touched'}: {path}",
            results={"path": path, "state": "touch"},
        )
    
    async def _ensure_file(self, path: str) -> ModuleResult:
        """Ensure path exists and is a file on Windows."""
        script = f'''
$path = "{path}"
if (-not (Test-Path -LiteralPath $path)) {{
    Write-Error "Path does not exist"
    exit 1
}}
if (Test-Path -LiteralPath $path -PathType Container) {{
    Write-Error "Path is a directory, not a file"
    exit 1
}}
Write-Output "exists"
'''
        result = await self.connection.run(script)
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=result.stderr.strip() or f"Path check failed for {path}",
            )
        
        return ModuleResult(
            changed=False,
            msg=f"File exists: {path}",
            results={"path": path, "state": "file"},
        )
