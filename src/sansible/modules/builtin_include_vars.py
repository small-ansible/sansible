"""
Sansible include_vars module

Load variables from files.
"""

import json
import os
from typing import Any, Dict

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class IncludeVarsModule(Module):
    """
    Load variables from YAML/JSON files.
    
    Variables loaded are set at the play level.
    """
    
    name = "include_vars"
    required_args = []  # Either "file" or "dir" or free-form (first positional)
    optional_args = {
        "file": None,           # Path to vars file
        "dir": None,            # Path to directory of vars files
        "name": None,           # Name of variable to store loaded vars
        "depth": 0,             # Depth of directory recursion (0 = unlimited)
        "files_matching": None,  # Pattern to match files
        "ignore_unknown_extensions": True,
        "extensions": ["yaml", "yml", "json"],
    }
    
    async def run(self) -> ModuleResult:
        """Load variables from file(s)."""
        # Handle free-form argument
        file_path = self.get_arg("file")
        if not file_path and "free_form" in self.args:
            file_path = self.args["free_form"]
        
        dir_path = self.get_arg("dir")
        var_name = self.get_arg("name")
        
        if not file_path and not dir_path:
            return ModuleResult(
                failed=True,
                msg="Either 'file' or 'dir' must be specified",
            )
        
        loaded_vars: Dict[str, Any] = {}
        files_loaded = []
        
        if file_path:
            # Load single file
            vars_data = await self._load_vars_file(file_path)
            if vars_data is None:
                return ModuleResult(
                    failed=True,
                    msg=f"Could not load vars file: {file_path}",
                )
            loaded_vars.update(vars_data)
            files_loaded.append(file_path)
        
        if dir_path:
            # Load all files from directory
            dir_vars, dir_files = await self._load_vars_dir(dir_path)
            loaded_vars.update(dir_vars)
            files_loaded.extend(dir_files)
        
        # If 'name' is specified, nest all vars under that key
        if var_name:
            result_vars = {var_name: loaded_vars}
        else:
            result_vars = loaded_vars
        
        return ModuleResult(
            changed=False,
            msg=f"Loaded {len(files_loaded)} vars file(s)",
            results={
                "ansible_included_var_files": files_loaded,
                "ansible_facts": result_vars,
            },
        )
    
    async def _load_vars_file(self, file_path: str) -> Dict[str, Any] | None:
        """Load a single vars file."""
        # Read file content (from control node, not remote)
        try:
            with open(file_path, "r") as f:
                content = f.read()
        except FileNotFoundError:
            # Try relative to playbook
            return None
        except Exception:
            return None
        
        # Parse based on extension
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext in (".yml", ".yaml"):
                import yaml
                return yaml.safe_load(content) or {}
            elif ext == ".json":
                return json.loads(content)
            else:
                # Try YAML first, then JSON
                import yaml
                try:
                    return yaml.safe_load(content) or {}
                except Exception:
                    return json.loads(content)
        except Exception:
            return None
    
    async def _load_vars_dir(self, dir_path: str) -> tuple[Dict[str, Any], list[str]]:
        """Load all vars files from a directory."""
        extensions = self.get_arg("extensions", ["yaml", "yml", "json"])
        pattern = self.get_arg("files_matching")
        
        result_vars: Dict[str, Any] = {}
        files_loaded = []
        
        try:
            for filename in sorted(os.listdir(dir_path)):
                # Check extension
                ext = os.path.splitext(filename)[1].lstrip(".")
                if ext not in extensions:
                    continue
                
                # Check pattern
                if pattern:
                    import fnmatch
                    if not fnmatch.fnmatch(filename, pattern):
                        continue
                
                file_path = os.path.join(dir_path, filename)
                if os.path.isfile(file_path):
                    vars_data = await self._load_vars_file(file_path)
                    if vars_data:
                        result_vars.update(vars_data)
                        files_loaded.append(file_path)
        except Exception:
            pass
        
        return result_vars, files_loaded
