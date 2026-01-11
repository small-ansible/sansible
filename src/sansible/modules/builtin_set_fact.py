"""
Sansible set_fact module

Set host facts (variables) during playbook execution.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class SetFactModule(Module):
    """
    Set host facts from task.
    
    Variables set with set_fact are available for subsequent tasks
    on the same host.
    """
    
    name = "set_fact"
    required_args = []
    optional_args = {
        "cacheable": False,  # Not implemented
    }
    
    async def run(self) -> ModuleResult:
        """Set the facts."""
        # All non-keyword arguments are treated as facts
        facts = {}
        for key, value in self.args.items():
            if key not in ('cacheable',):
                facts[key] = value
                # Set the variable in the host context
                self.context.vars[key] = value
        
        return ModuleResult(
            changed=False,  # set_fact is not considered a change
            msg=f"Set {len(facts)} fact(s)",
            results={"ansible_facts": facts},
        )
