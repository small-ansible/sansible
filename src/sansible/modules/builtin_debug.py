"""
Sansible debug module

Print debug messages during playbook execution.
"""

import json

from sansible.modules.base import Module, ModuleResult, register_module


def _resolve_dotted_var(data: dict, var_path: str):
    """
    Resolve a dotted variable path like 'cmd_result.stdout'.
    
    Returns the value or raises KeyError if not found.
    """
    parts = var_path.split('.')
    value = data
    for part in parts:
        if isinstance(value, dict):
            if part not in value:
                raise KeyError(part)
            value = value[part]
        elif isinstance(value, list):
            try:
                idx = int(part)
                value = value[idx]
            except (ValueError, IndexError):
                raise KeyError(part)
        else:
            raise KeyError(part)
    return value


@register_module
class DebugModule(Module):
    """
    Print debug messages.
    
    Useful for printing variable values and troubleshooting playbooks.
    """
    
    name = "debug"
    required_args = []
    optional_args = {
        "msg": "Hello world!",
        "var": None,
        "verbosity": 0,
    }
    
    async def run(self) -> ModuleResult:
        """Print the debug message."""
        msg = self.get_arg("msg")
        var = self.get_arg("var")
        verbosity = self.get_arg("verbosity", 0)
        
        # Get variable value if specified
        if var:
            try:
                var_value = _resolve_dotted_var(self.context.get_vars(), var)
            except KeyError:
                var_value = "VARIABLE IS NOT DEFINED!"
            if isinstance(var_value, (dict, list)):
                output = f"{var}: {json.dumps(var_value, indent=2)}"
            else:
                output = f"{var}: {var_value}"
        else:
            output = str(msg)
        
        return ModuleResult(
            changed=False,
            msg=output,
            results={"msg": output},
        )
