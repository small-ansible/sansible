"""
Sansible replace module

Replace all instances of a pattern within a file.
"""

import re
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class ReplaceModule(Module):
    """
    Replace all instances of a particular string in a file using regex.
    """
    
    name = "replace"
    required_args = ["path", "regexp"]
    optional_args = {
        "replace": "",
        "backup": False,
        "after": None,
        "before": None,
        "encoding": "utf-8",
    }
    
    async def run(self) -> ModuleResult:
        """Replace pattern occurrences in file."""
        path = self.args["path"]
        regexp = self.args["regexp"]
        replace_str = self.get_arg("replace", "")
        after = self.get_arg("after")
        before = self.get_arg("before")
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Read current file content
        result = await self.connection.run(f"cat '{path}'", shell=True)
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"File not found: {path}",
            )
        
        content = result.stdout
        original_content = content
        
        # Handle after/before constraints
        if after or before:
            # Find the section to work on
            start_idx = 0
            end_idx = len(content)
            
            if after:
                after_match = re.search(after, content)
                if after_match:
                    start_idx = after_match.end()
            
            if before:
                before_match = re.search(before, content[start_idx:])
                if before_match:
                    end_idx = start_idx + before_match.start()
            
            # Only replace in the selected section
            section = content[start_idx:end_idx]
            new_section = re.sub(regexp, replace_str, section)
            content = content[:start_idx] + new_section + content[end_idx:]
        else:
            content = re.sub(regexp, replace_str, content)
        
        changed = content != original_content
        
        if self.context.check_mode:
            return ModuleResult(
                changed=changed,
                msg=f"Pattern would be {'replaced' if changed else 'unchanged'} in {path}",
            )
        
        if changed:
            # Escape content for shell
            escaped = content.replace("'", "'\"'\"'")
            write_cmd = f"printf '%s' '{escaped}' > '{path}'"
            
            result = await self.connection.run(write_cmd, shell=True)
            if result.rc != 0:
                return ModuleResult(
                    failed=True,
                    msg=f"Failed to write file: {result.stderr}",
                )
        
        return ModuleResult(
            changed=changed,
            msg=f"Pattern {'replaced' if changed else 'unchanged'} in {path}",
            results={"path": path},
        )
