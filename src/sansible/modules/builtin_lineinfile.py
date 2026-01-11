"""
Sansible lineinfile module

Manage lines in text files.
"""

import re
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class LineinfileModule(Module):
    """
    Ensure a particular line is in a file, or replace an existing line.
    
    Similar to Ansible's lineinfile module but with a simpler implementation.
    """
    
    name = "lineinfile"
    required_args = ["path"]
    optional_args = {
        "line": None,  # Line to insert/ensure
        "regexp": None,  # Pattern to match for replacement
        "state": "present",  # present or absent
        "create": False,  # Create file if missing
        "backup": False,  # Create backup
        "insertafter": "EOF",  # Where to insert (EOF, BOF, or regexp)
        "insertbefore": None,  # Insert before this pattern
    }
    
    async def run(self) -> ModuleResult:
        """Manage lines in a file."""
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
        
        # State validation
        if state == "present" and line is None:
            return ModuleResult(
                failed=True,
                msg="'line' is required when state=present",
            )
        
        if state == "absent" and line is None and regexp is None:
            return ModuleResult(
                failed=True,
                msg="'line' or 'regexp' required when state=absent",
            )
        
        # Read current file content
        try:
            result = await self.connection.run(f"cat {path}", shell=True)
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
        original_lines = lines.copy()
        changed = False
        
        if state == "present":
            changed = self._ensure_present(lines, line, regexp)
        else:  # absent
            changed = self._ensure_absent(lines, line, regexp)
        
        # Check mode - don't write
        if self.context.check_mode:
            return ModuleResult(
                changed=changed,
                msg=f"{'Would change' if changed else 'No change to'} {path}",
            )
        
        # Write if changed
        if changed:
            new_content = "\n".join(lines)
            if content.endswith("\n"):
                new_content += "\n"
            
            # Escape content for shell
            escaped = new_content.replace("'", "'\"'\"'")
            write_cmd = f"printf '%s' '{escaped}' > {path}"
            
            try:
                result = await self.connection.run(write_cmd, shell=True)
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
            msg=f"{'Line added' if changed else 'Line already present'}" if state == "present" 
                else f"{'Line removed' if changed else 'Line not present'}",
        )
    
    def _ensure_present(self, lines: list, line: str, regexp: str = None) -> bool:
        """Ensure line is present, optionally matching regexp."""
        if regexp:
            pattern = re.compile(regexp)
            for i, existing in enumerate(lines):
                if pattern.search(existing):
                    if existing != line:
                        lines[i] = line
                        return True
                    return False  # Already matches
            # No match found, append
            lines.append(line)
            return True
        else:
            # Simple line match
            if line in lines:
                return False
            lines.append(line)
            return True
    
    def _ensure_absent(self, lines: list, line: str = None, regexp: str = None) -> bool:
        """Remove matching lines."""
        changed = False
        
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
            changed = True
        
        return changed
