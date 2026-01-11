"""
Sansible assert module

Assert conditions during playbook execution.
"""

from typing import List

from sansible.engine.templating import evaluate_when
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class AssertModule(Module):
    """
    Assert conditions are true.
    
    Useful for validating state before proceeding with tasks.
    """
    
    name = "assert"
    required_args = ["that"]
    optional_args = {
        "msg": None,
        "success_msg": None,
        "fail_msg": None,
        "quiet": False,
    }
    
    async def run(self) -> ModuleResult:
        """Evaluate assertions."""
        that = self.args["that"]
        msg = self.get_arg("msg") or self.get_arg("fail_msg")
        success_msg = self.get_arg("success_msg")
        quiet = self.get_arg("quiet", False)
        
        # Ensure 'that' is a list
        if isinstance(that, str):
            conditions = [that]
        else:
            conditions = list(that)
        
        # Evaluate each condition
        host_vars = self.context.get_vars()
        failed_conditions = []
        
        for condition in conditions:
            try:
                result = evaluate_when(condition, host_vars)
                if not result:
                    failed_conditions.append(condition)
            except Exception as e:
                failed_conditions.append(f"{condition} (error: {e})")
        
        if failed_conditions:
            fail_message = msg or f"Assertion failed: {', '.join(failed_conditions)}"
            return ModuleResult(
                changed=False,
                failed=True,
                msg=fail_message,
                results={"failed_conditions": failed_conditions},
            )
        
        success_message = success_msg or "All assertions passed"
        return ModuleResult(
            changed=False,
            msg="" if quiet else success_message,
            results={"evaluated": conditions},
        )
