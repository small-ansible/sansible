"""
Sansible meta module

Meta actions for playbook execution control.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class MetaModule(Module):
    """
    Execute Ansible meta tasks.
    
    Meta tasks control the internal execution state of Ansible.
    """
    
    name = "meta"
    required_args = []
    optional_args = {
        "free_form": None,      # The meta action (flush_handlers, etc.)
    }
    
    # Supported meta actions
    SUPPORTED_ACTIONS = {
        "flush_handlers",       # Run any pending handlers
        "clear_facts",          # Clear gathered facts for a host
        "clear_host_errors",    # Clear any errors for a host
        "end_play",             # End the play for the current host
        "end_host",             # End tasks for the current host
        "end_batch",            # End batch (for serial)
        "reset_connection",     # Reset the connection to a host
        "noop",                 # Do nothing
        "refresh_inventory",    # Refresh dynamic inventory
    }
    
    async def run(self) -> ModuleResult:
        """Execute meta action."""
        action = self.get_arg("free_form") or self.args.get("_raw_params", "")
        
        if not action:
            # Try to get from first positional arg
            for key, value in self.args.items():
                if key not in ("_raw_params", "free_form"):
                    action = key
                    break
        
        if not action:
            return ModuleResult(
                failed=True,
                msg="No meta action specified",
            )
        
        action = action.strip()
        
        if action not in self.SUPPORTED_ACTIONS:
            return ModuleResult(
                failed=True,
                msg=f"Unknown meta action: {action}. Supported: {', '.join(sorted(self.SUPPORTED_ACTIONS))}",
            )
        
        # Return the meta action for the engine to handle
        return ModuleResult(
            changed=False,
            msg=f"Meta action: {action}",
            results={
                "meta_action": action,
            },
        )
