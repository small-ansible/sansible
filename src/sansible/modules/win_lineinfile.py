"""
Sansible win_lineinfile module

Manage lines in text files on Windows.
"""

import re
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WinLineinfileModule(Module):
    """
    Ensure a particular line is in a file on Windows.
    
    Uses PowerShell for file operations.
    """
    
    name = "win_lineinfile"
    required_args = ["path"]
    optional_args = {
        "line": None,
        "regexp": None,
        "state": "present",
        "create": False,
        "backup": False,
        "newline": "windows",  # windows (\r\n) or unix (\n)
    }
    
    async def run(self) -> ModuleResult:
        """Manage lines in a Windows file."""
        path = self.args["path"]
        line = self.args.get("line")
        regexp = self.args.get("regexp")
        state = self.args.get("state", "present")
        create = self.args.get("create", False)
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        if state == "present" and line is None:
            return ModuleResult(
                failed=True,
                msg="'line' is required when state=present",
            )
        
        # Read file with PowerShell
        read_ps = f'''
$path = "{path}"
if (Test-Path -LiteralPath $path) {{
    Get-Content -LiteralPath $path -Raw
}} else {{
    Write-Error "FILE_NOT_FOUND"
    exit 1
}}
'''
        
        try:
            result = await self.connection.run(read_ps, shell=True)
            if result.rc != 0:
                if create and state == "present":
                    content = ""
                else:
                    return ModuleResult(
                        failed=True,
                        msg=f"File not found: {path}",
                    )
            else:
                content = result.stdout
        except Exception as e:
            return ModuleResult(
                failed=True,
                msg=f"Failed to read file: {e}",
            )
        
        lines = content.splitlines()
        original_count = len(lines)
        changed = False
        
        if state == "present":
            changed = self._ensure_present(lines, line, regexp)
        else:
            changed = self._ensure_absent(lines, line, regexp)
        
        if self.context.check_mode:
            return ModuleResult(
                changed=changed,
                msg=f"{'Would change' if changed else 'No change to'} {path}",
            )
        
        if changed:
            newline = "\r\n" if self.args.get("newline", "windows") == "windows" else "\n"
            new_content = newline.join(lines)
            
            # Escape for PowerShell
            escaped = new_content.replace('"', '`"').replace('$', '`$')
            write_ps = f'''
$content = "{escaped}"
Set-Content -LiteralPath "{path}" -Value $content -NoNewline
'''
            
            try:
                result = await self.connection.run(write_ps, shell=True)
                if result.rc != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"Failed to write file: {result.stderr}",
                    )
            except Exception as e:
                return ModuleResult(
                    failed=True,
                    msg=f"Failed to write file: {e}",
                )
        
        return ModuleResult(
            changed=changed,
            msg=f"{'Line managed' if changed else 'No change needed'}",
        )
    
    def _ensure_present(self, lines: list, line: str, regexp: str = None) -> bool:
        """Ensure line is present."""
        if regexp:
            pattern = re.compile(regexp)
            for i, existing in enumerate(lines):
                if pattern.search(existing):
                    if existing != line:
                        lines[i] = line
                        return True
                    return False
            lines.append(line)
            return True
        else:
            if line in lines:
                return False
            lines.append(line)
            return True
    
    def _ensure_absent(self, lines: list, line: str = None, regexp: str = None) -> bool:
        """Remove matching lines."""
        if regexp:
            pattern = re.compile(regexp)
            new_lines = [l for l in lines if not pattern.search(l)]
        elif line:
            new_lines = [l for l in lines if l != line]
        else:
            return False
        
        if len(new_lines) != len(lines):
            lines.clear()
            lines.extend(new_lines)
            return True
        return False
