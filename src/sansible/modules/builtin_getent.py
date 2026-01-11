"""
Sansible getent module

Query getent databases (passwd, group, hosts, etc).
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class GetentModule(Module):
    """
    Query getent databases for user/group/host information.
    """
    
    name = "getent"
    required_args = ["database"]
    optional_args = {
        "key": None,
        "split": None,
        "fail_key": True,
    }
    
    async def run(self) -> ModuleResult:
        """Query getent database."""
        database = self.args["database"]
        key = self.get_arg("key")
        split = self.get_arg("split")
        fail_key = self.get_arg("fail_key", True)
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Build getent command
        cmd = f"getent {database}"
        if key:
            cmd += f" {key}"
        
        result = await self.connection.run(cmd, shell=True)
        
        if result.rc != 0:
            if key and not fail_key:
                return ModuleResult(
                    changed=False,
                    msg=f"Key '{key}' not found in {database}",
                    results={f"ansible_facts": {f"getent_{database}": {}}},
                )
            return ModuleResult(
                failed=True,
                msg=f"getent failed: {result.stderr or result.stdout}",
            )
        
        # Parse output
        entries = {}
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            
            if split:
                parts = line.split(split)
            else:
                parts = line.split(':')
            
            if parts:
                entry_key = parts[0]
                entries[entry_key] = parts[1:] if len(parts) > 1 else []
        
        return ModuleResult(
            changed=False,
            msg=f"Queried {database}",
            results={
                "ansible_facts": {
                    f"getent_{database}": entries,
                },
            },
        )
