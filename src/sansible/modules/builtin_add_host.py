"""
Sansible add_host module

Add a host to in-memory inventory.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class AddHostModule(Module):
    """
    Add a host to the in-memory inventory.
    
    This allows dynamic addition of hosts during playbook execution.
    """
    
    name = "add_host"
    required_args = ["name"]
    optional_args = {
        "groups": [],           # Groups to add the host to
        "group": None,          # Alternative single group
    }
    
    async def run(self) -> ModuleResult:
        """Add host to inventory."""
        hostname = self.args["name"]
        groups = self.get_arg("groups", [])
        single_group = self.get_arg("group")
        
        # Handle groups parameter
        if isinstance(groups, str):
            groups = [g.strip() for g in groups.split(",")]
        
        if single_group:
            if single_group not in groups:
                groups.append(single_group)
        
        # Also capture any extra variables
        extra_vars = {}
        for key, value in self.args.items():
            if key not in ("name", "groups", "group"):
                extra_vars[key] = value
        
        # Note: In Sansible, the actual inventory modification happens
        # at the engine level. This module just returns what should be added.
        return ModuleResult(
            changed=True,
            msg=f"Added host {hostname}",
            results={
                "add_host": {
                    "host_name": hostname,
                    "groups": groups,
                    "host_vars": extra_vars,
                },
            },
        )
