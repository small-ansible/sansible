"""
Sansible ping module

A trivial test module that returns 'pong' on success.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class PingModule(Module):
    """
    A trivial test module that always succeeds.
    
    This module is mostly useful for testing connectivity and
    verifying that a host is reachable and can run modules.
    """
    
    name = "ping"
    required_args = []
    optional_args = {
        "data": "pong",
    }
    
    async def run(self) -> ModuleResult:
        """Return pong (or custom data)."""
        data = self.get_arg("data", "pong")
        
        return ModuleResult(
            changed=False,
            msg=data,
            results={"ping": data},
        )
