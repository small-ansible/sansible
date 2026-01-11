"""
Sansible find module

Find files matching criteria on remote systems.
"""

import fnmatch
from typing import List

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class FindModule(Module):
    """
    Find files and directories matching criteria.
    
    Returns a list of files/directories that match the given criteria.
    """
    
    name = "find"
    required_args = ["paths"]
    optional_args = {
        "patterns": ["*"],          # File patterns (shell globs)
        "excludes": [],             # Patterns to exclude
        "file_type": "file",        # file, directory, link, any
        "recurse": False,           # Recurse into subdirectories
        "depth": None,              # Maximum depth to recurse
        "age": None,                # Age filter (e.g., "1d", "-1w")
        "size": None,               # Size filter (e.g., "1m", "-1g")
        "hidden": False,            # Include hidden files
        "follow": False,            # Follow symlinks
    }
    
    async def run(self) -> ModuleResult:
        """Find files matching criteria."""
        paths = self.args["paths"]
        if isinstance(paths, str):
            paths = [paths]
        
        patterns = self.get_arg("patterns", ["*"])
        if isinstance(patterns, str):
            patterns = [patterns]
        
        excludes = self.get_arg("excludes", [])
        if isinstance(excludes, str):
            excludes = [excludes]
        
        file_type = self.get_arg("file_type", "file")
        recurse = self.get_arg("recurse", False)
        depth = self.get_arg("depth")
        hidden = self.get_arg("hidden", False)
        
        # Build find command
        cmd_parts = ["find"]
        cmd_parts.extend(paths)
        
        # Depth limit
        if depth is not None:
            cmd_parts.extend(["-maxdepth", str(depth)])
        elif not recurse:
            cmd_parts.extend(["-maxdepth", "1"])
        
        # File type
        if file_type == "file":
            cmd_parts.extend(["-type", "f"])
        elif file_type == "directory":
            cmd_parts.extend(["-type", "d"])
        elif file_type == "link":
            cmd_parts.extend(["-type", "l"])
        # "any" - no type filter
        
        # Hidden files filter
        if not hidden:
            cmd_parts.extend(["!", "-name", ".*"])
        
        # Pattern matching - use -name or -iname
        if patterns and patterns != ["*"]:
            if len(patterns) == 1:
                cmd_parts.extend(["-name", patterns[0]])
            else:
                cmd_parts.append("(")
                for i, pattern in enumerate(patterns):
                    if i > 0:
                        cmd_parts.append("-o")
                    cmd_parts.extend(["-name", pattern])
                cmd_parts.append(")")
        
        # Excludes
        for exclude in excludes:
            cmd_parts.extend(["!", "-name", exclude])
        
        # Age filter
        age = self.get_arg("age")
        if age:
            # Parse age like "1d", "-1w", "+30m"
            age_cmd = self._parse_age(age)
            if age_cmd:
                cmd_parts.extend(age_cmd)
        
        # Size filter
        size = self.get_arg("size")
        if size:
            size_cmd = self._parse_size(size)
            if size_cmd:
                cmd_parts.extend(size_cmd)
        
        # Print results with details
        cmd_parts.extend(["-printf", "%p\\n"])
        
        cmd = " ".join(cmd_parts)
        result = await self.connection.run(cmd, shell=True)
        
        if result.rc not in (0, 1):  # 1 can mean "no files found"
            return ModuleResult(
                failed=True,
                msg=f"Find command failed: {result.stderr}",
            )
        
        # Parse output
        files: List[dict] = []
        for line in result.stdout.strip().split("\n"):
            if line:
                files.append({"path": line})
        
        return ModuleResult(
            changed=False,
            msg=f"Found {len(files)} file(s)",
            results={
                "files": files,
                "matched": len(files),
                "examined": len(files),
            },
        )
    
    def _parse_age(self, age: str) -> List[str]:
        """Parse age string like '1d', '-1w', '+30m'."""
        import re
        match = re.match(r"([+-]?)(\d+)([smhdw]?)", age)
        if not match:
            return []
        
        sign, num, unit = match.groups()
        
        # Convert to days for find command
        multipliers = {"s": 1/86400, "m": 1/1440, "h": 1/24, "d": 1, "w": 7}
        days = int(num) * multipliers.get(unit or "d", 1)
        
        if sign == "-":
            return ["-mtime", f"-{int(days)}"]
        elif sign == "+":
            return ["-mtime", f"+{int(days)}"]
        else:
            return ["-mtime", str(int(days))]
    
    def _parse_size(self, size: str) -> List[str]:
        """Parse size string like '1m', '-1g', '+100k'."""
        import re
        match = re.match(r"([+-]?)(\d+)([bkmg]?)", size.lower())
        if not match:
            return []
        
        sign, num, unit = match.groups()
        
        # Convert to find's size format
        size_map = {"b": "c", "k": "k", "m": "M", "g": "G"}
        find_unit = size_map.get(unit, "c")
        
        return ["-size", f"{sign}{num}{find_unit}"]
