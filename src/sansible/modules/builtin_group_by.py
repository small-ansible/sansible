"""
Sansible group_by module

Create groups based on facts.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class GroupByModule(Module):
    """
    Create groups based on the value of a variable.
    
    This allows dynamic grouping of hosts based on gathered facts
    or other variables.
    """
    
    name = "group_by"
    required_args = ["key"]
    optional_args = {
        "parents": [],          # Parent groups to add the new group to
    }
    
    async def run(self) -> ModuleResult:
        """Create group based on key value."""
        key = self.args["key"]
        parents = self.get_arg("parents", [])
        
        if isinstance(parents, str):
            parents = [p.strip() for p in parents.split(",")]
        
        # The key is a Jinja2 expression that should already be templated
        # by the time it reaches the module
        group_name = str(key)
        
        # Sanitize group name (replace problematic characters)
        group_name = group_name.replace("-", "_").replace(" ", "_")
        
        # Note: Actual group creation happens at the engine level.
        # This module returns what group the host should be added to.
        return ModuleResult(
            changed=True,
            msg=f"Added host to group {group_name}",
            results={
                "group_by": {
                    "group_name": group_name,
                    "parent_groups": parents,
                },
            },
        )
