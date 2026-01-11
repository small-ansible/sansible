"""
Sansible debug module

Print debug messages during playbook execution.
"""

import json

from sansible.modules.base import Module, ModuleResult, register_module


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
            var_value = self.context.get_vars().get(var, "VARIABLE IS NOT DEFINED!")
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
