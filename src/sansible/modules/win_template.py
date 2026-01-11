"""
Sansible win_template module

Template files for Windows targets.
"""

import os
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WinTemplateModule(Module):
    """
    Template a file to a Windows remote host using Jinja2.
    """
    
    name = "win_template"
    required_args = ["src", "dest"]
    optional_args = {
        "backup": False,
        "force": True,
        "newline_sequence": "\\r\\n",
    }
    
    async def run(self) -> ModuleResult:
        """Render template and copy to Windows host."""
        src = self.args["src"]
        dest = self.args["dest"]
        backup = self.get_arg("backup", False)
        force = self.get_arg("force", True)
        newline_sequence = self.get_arg("newline_sequence", "\\r\\n")
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Find template file
        if not os.path.isabs(src):
            if hasattr(self.context, 'playbook_dir') and self.context.playbook_dir:
                # Try templates directory first
                template_path = os.path.join(self.context.playbook_dir, 'templates', src)
                if os.path.exists(template_path):
                    src = template_path
                else:
                    # Try relative to playbook
                    src = os.path.join(self.context.playbook_dir, src)
        
        if not os.path.exists(src):
            return ModuleResult(
                failed=True,
                msg=f"Template not found: {src}",
            )
        
        # Read template
        with open(src, 'r') as f:
            template_content = f.read()
        
        # Render template using Jinja2
        try:
            from jinja2 import Environment, StrictUndefined
            
            env = Environment(undefined=StrictUndefined)
            template = env.from_string(template_content)
            
            # Build template variables from context
            template_vars = {}
            if hasattr(self.context, 'hostvars'):
                template_vars.update(self.context.hostvars)
            
            # Add host info
            if hasattr(self.context, 'host'):
                template_vars['inventory_hostname'] = self.context.host.name
            
            rendered = template.render(**template_vars)
        except Exception as e:
            return ModuleResult(
                failed=True,
                msg=f"Template rendering failed: {e}",
            )
        
        # Handle newlines for Windows
        if newline_sequence == "\\r\\n":
            rendered = rendered.replace('\n', '\r\n').replace('\r\r\n', '\r\n')
        
        if self.context.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"Would template {src} to {dest}",
            )
        
        # Check if dest exists and compare
        if not force:
            check_cmd = f"Test-Path -Path '{dest}'"
            result = await self.connection.run(check_cmd, shell=True)
            if 'True' in result.stdout:
                return ModuleResult(
                    changed=False,
                    msg=f"Destination exists and force=false",
                )
        
        # Backup if requested
        if backup:
            backup_cmd = f"""
if (Test-Path -Path '{dest}') {{
    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    Copy-Item -Path '{dest}' -Destination ('{dest}.' + $timestamp + '.bak')
}}
"""
            await self.connection.run(backup_cmd, shell=True)
        
        # Write content using PowerShell
        # Escape for PowerShell
        escaped = rendered.replace("'", "''")
        write_cmd = f"Set-Content -Path '{dest}' -Value @'\n{escaped}\n'@ -NoNewline"
        
        result = await self.connection.run(write_cmd, shell=True)
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to write template: {result.stderr}",
            )
        
        return ModuleResult(
            changed=True,
            msg=f"Templated {src} to {dest}",
            results={"src": src, "dest": dest},
        )
