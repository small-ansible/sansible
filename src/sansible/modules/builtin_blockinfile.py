"""
Sansible blockinfile module

Insert/update/remove a text block surrounded by marker lines.
"""

import re
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class BlockinfileModule(Module):
    """
    Insert/update/remove a text block surrounded by marker lines.
    
    Similar to lineinfile but handles multi-line blocks.
    """
    
    name = "blockinfile"
    required_args = ["path"]
    optional_args = {
        "block": "",
        "marker": "# {mark} ANSIBLE MANAGED BLOCK",
        "marker_begin": "BEGIN",
        "marker_end": "END",
        "insertafter": "EOF",
        "insertbefore": None,
        "create": False,
        "backup": False,
        "state": "present",
    }
    
    async def run(self) -> ModuleResult:
        """Insert/update/remove text block."""
        path = self.args["path"]
        block = self.get_arg("block", "")
        marker = self.get_arg("marker", "# {mark} ANSIBLE MANAGED BLOCK")
        marker_begin = self.get_arg("marker_begin", "BEGIN")
        marker_end = self.get_arg("marker_end", "END")
        insertafter = self.get_arg("insertafter", "EOF")
        insertbefore = self.get_arg("insertbefore")
        create = self.get_arg("create", False)
        state = self.get_arg("state", "present")
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Build markers
        begin_marker = marker.replace("{mark}", marker_begin)
        end_marker = marker.replace("{mark}", marker_end)
        
        # Read current file content
        result = await self.connection.run(f"cat '{path}'", shell=True)
        if result.rc != 0:
            if create:
                content = ""
            else:
                return ModuleResult(
                    failed=True,
                    msg=f"File not found: {path}",
                )
        else:
            content = result.stdout
        
        lines = content.splitlines(keepends=True)
        
        # Find existing block
        begin_idx = None
        end_idx = None
        for i, line in enumerate(lines):
            if begin_marker in line.rstrip('\n\r'):
                begin_idx = i
            elif end_marker in line.rstrip('\n\r'):
                end_idx = i
                break
        
        # Prepare the new block
        if state == "present" and block:
            # Ensure block ends with newline
            if block and not block.endswith('\n'):
                block += '\n'
            new_block_lines = [
                begin_marker + '\n',
                block,
                end_marker + '\n',
            ]
        else:
            new_block_lines = []
        
        changed = False
        
        if begin_idx is not None and end_idx is not None:
            # Block exists - replace or remove
            old_block = ''.join(lines[begin_idx:end_idx + 1])
            new_block = ''.join(new_block_lines)
            
            if old_block != new_block:
                lines = lines[:begin_idx] + new_block_lines + lines[end_idx + 1:]
                changed = True
        elif state == "present" and block:
            # Block doesn't exist - insert it
            if insertbefore == "BOF":
                lines = new_block_lines + lines
            elif insertafter == "EOF" or not insertafter:
                # Ensure file ends with newline before adding block
                if lines and not lines[-1].endswith('\n'):
                    lines[-1] += '\n'
                lines = lines + new_block_lines
            else:
                # Try to find insertafter pattern
                insert_pos = len(lines)
                pattern = re.compile(insertafter)
                for i, line in enumerate(lines):
                    if pattern.search(line):
                        insert_pos = i + 1
                lines = lines[:insert_pos] + new_block_lines + lines[insert_pos:]
            changed = True
        
        if self.context.check_mode:
            return ModuleResult(
                changed=changed,
                msg=f"Block would be {'updated' if changed else 'unchanged'} in {path}",
            )
        
        if changed:
            new_content = ''.join(lines)
            # Escape content for shell
            escaped = new_content.replace("'", "'\"'\"'")
            write_cmd = f"printf '%s' '{escaped}' > '{path}'"
            
            result = await self.connection.run(write_cmd, shell=True)
            if result.rc != 0:
                return ModuleResult(
                    failed=True,
                    msg=f"Failed to write file: {result.stderr}",
                )
        
        return ModuleResult(
            changed=changed,
            msg=f"Block {'updated' if changed else 'unchanged'} in {path}",
            results={"path": path},
        )
