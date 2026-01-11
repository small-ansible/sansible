"""
Sansible fail module

Fail playbook execution with a message.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class FailModule(Module):
    """
    Fail playbook execution.
    
    Use this to explicitly fail a playbook based on conditions.
    """
    
    name = "fail"
    required_args = []
    optional_args = {
        "msg": "Failed as requested from task",
    }
    
    async def run(self) -> ModuleResult:
        """Fail with message."""
        msg = self.get_arg("msg", "Failed as requested from task")
        
        return ModuleResult(
            changed=False,
            failed=True,
            msg=msg,
        )
