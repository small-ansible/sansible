"""
Galaxy Module

A dynamic module wrapper that executes Galaxy collection modules via
remote ansible-core installation (Strategy A).
"""

from typing import Any, Dict, Optional

from sansible.modules.base import Module, ModuleResult
from sansible.engine.scheduler import HostContext
from sansible.galaxy.loader import GalaxyModuleLoader
from sansible.galaxy.executor import GalaxyModuleExecutor


class GalaxyModule(Module):
    """
    Dynamic module wrapper for Ansible Galaxy collection modules.
    
    This module executes Galaxy modules by:
    1. Ensuring ansible-core is installed on the remote host
    2. Installing the required collection
    3. Executing the module via ansible's native execution
    4. Parsing the JSON output
    
    Usage in runner:
        if GalaxyModuleLoader.is_galaxy_module(module_name):
            module = GalaxyModule(module_name, args, context)
            result = await module.run()
    """
    
    name = "_galaxy"  # Internal name, actual module name is dynamic
    required_args = []
    optional_args = {}
    
    def __init__(
        self,
        module_name: str,
        args: Dict[str, Any],
        context: HostContext,
    ):
        """
        Initialize Galaxy module wrapper.
        
        Args:
            module_name: Full Galaxy module name (e.g., "community.general.timezone")
            args: Module arguments from playbook
            context: Host context
        """
        super().__init__(args, context)
        self.module_name = module_name
        self._loader: Optional[GalaxyModuleLoader] = None
        self._executor: Optional[GalaxyModuleExecutor] = None
    
    @property
    def loader(self) -> GalaxyModuleLoader:
        """Get or create the loader."""
        if self._loader is None:
            is_windows = self._detect_windows()
            self._loader = GalaxyModuleLoader(self.connection, is_windows)
        return self._loader
    
    @property
    def executor(self) -> GalaxyModuleExecutor:
        """Get or create the executor."""
        if self._executor is None:
            self._executor = GalaxyModuleExecutor(
                self.connection,
                self.loader,
                check_mode=self.check_mode,
                diff_mode=self.diff_mode,
            )
        return self._executor
    
    def _detect_windows(self) -> bool:
        """Detect if target is Windows."""
        if self.host:
            connection_type = self.host.get_variable("ansible_connection", "")
            return connection_type in ("winrm", "psrp")
        return False
    
    def validate_args(self) -> Optional[str]:
        """
        Validate module arguments.
        
        Galaxy modules handle their own validation, so we just check
        that the module name is valid.
        """
        if not GalaxyModuleLoader.is_galaxy_module(self.module_name):
            return f"Invalid Galaxy module name: {self.module_name}"
        return None
    
    async def run(self) -> ModuleResult:
        """
        Execute the Galaxy module.
        
        Returns:
            ModuleResult with execution outcome
        """
        # Get become settings from context
        become = self.context.become
        become_user = self.context.become_user
        become_method = self.context.become_method
        
        # Execute the module
        try:
            result = await self.executor.execute(
                module_name=self.module_name,
                args=self.args,
                become=become,
                become_user=become_user,
                become_method=become_method,
            )
            
            return ModuleResult(
                changed=result.get("changed", False),
                failed=result.get("failed", False),
                rc=result.get("rc", 0),
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                msg=result.get("msg", ""),
                results=result.get("results", {}),
            )
            
        except Exception as e:
            return ModuleResult(
                failed=True,
                msg=f"Galaxy module execution failed: {e}",
            )
    
    async def check(self) -> ModuleResult:
        """
        Execute the module in check mode.
        
        Returns:
            ModuleResult with predicted outcome
        """
        # The executor already handles check mode
        return await self.run()


def create_galaxy_module(
    module_name: str,
    args: Dict[str, Any],
    context: HostContext,
) -> GalaxyModule:
    """
    Factory function to create a Galaxy module instance.
    
    Args:
        module_name: Full Galaxy module name
        args: Module arguments
        context: Host context
        
    Returns:
        Configured GalaxyModule instance
    """
    return GalaxyModule(module_name, args, context)
