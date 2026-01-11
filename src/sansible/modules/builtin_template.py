"""
Sansible template module

Template a file to a remote host using Jinja2.
"""

import tempfile
from pathlib import Path
from typing import Optional

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class TemplateModule(Module):
    """
    Template a file to a remote host.
    
    Renders a Jinja2 template locally and copies the result to the remote host.
    
    Supports:
    - Jinja2 template rendering with access to all variables
    - Optional mode setting
    - Idempotency via content comparison
    """
    
    name = "template"
    required_args = ["src", "dest"]
    optional_args = {
        "mode": None,
        "owner": None,  # Not implemented in v0.1
        "group": None,  # Not implemented in v0.1
        "backup": False,
        "force": True,
        "newline_sequence": "\n",
        "output_encoding": "utf-8",
        "block_start_string": "{%",
        "block_end_string": "%}",
        "variable_start_string": "{{",
        "variable_end_string": "}}",
    }
    
    async def run(self) -> ModuleResult:
        """Render and copy the template."""
        src = self.args["src"]
        dest = self.args["dest"]
        mode = self.get_arg("mode")
        force = self.get_arg("force", True)
        newline_sequence = self.get_arg("newline_sequence", "\n")
        output_encoding = self.get_arg("output_encoding", "utf-8")
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Find the template file
        src_path = Path(src)
        if not src_path.is_absolute():
            # Try relative to playbook directory (from context vars)
            playbook_dir = self.context.vars.get("playbook_dir", ".")
            src_path = Path(playbook_dir) / src
        
        if not src_path.exists():
            return ModuleResult(
                failed=True,
                msg=f"Template file not found: {src}",
            )
        
        # Read the template
        try:
            template_content = src_path.read_text(encoding="utf-8")
        except Exception as e:
            return ModuleResult(
                failed=True,
                msg=f"Failed to read template {src}: {e}",
            )
        
        # Render the template using Jinja2
        try:
            from jinja2 import Environment, StrictUndefined, TemplateError
            
            env = Environment(
                undefined=StrictUndefined,
                keep_trailing_newline=True,
                block_start_string=self.get_arg("block_start_string", "{%"),
                block_end_string=self.get_arg("block_end_string", "%}"),
                variable_start_string=self.get_arg("variable_start_string", "{{"),
                variable_end_string=self.get_arg("variable_end_string", "}}"),
            )
            
            # Add common filters
            from sansible.engine.templating import CUSTOM_FILTERS
            for name, func in CUSTOM_FILTERS.items():
                env.filters[name] = func
            
            # Compile and render
            template = env.from_string(template_content)
            rendered = template.render(**self.context.vars)
            
            # Handle newline sequence
            if newline_sequence != "\n":
                rendered = rendered.replace("\n", newline_sequence)
            
        except TemplateError as e:
            return ModuleResult(
                failed=True,
                msg=f"Template rendering failed: {e}",
            )
        except Exception as e:
            return ModuleResult(
                failed=True,
                msg=f"Template error: {e}",
            )
        
        # Write rendered content to temp file
        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            suffix=".rendered",
            encoding=output_encoding,
        ) as f:
            f.write(rendered)
            temp_path = Path(f.name)
        
        try:
            # Check if destination exists with same content
            if not force:
                remote_stat = await self.connection.stat(dest)
                if remote_stat and remote_stat.get("exists"):
                    # Size-based idempotency check
                    local_size = len(rendered.encode(output_encoding))
                    if remote_stat.get("size") == local_size:
                        return ModuleResult(
                            changed=False,
                            msg="Template content already matches",
                            results={"src": src, "dest": dest},
                        )
            
            # Upload the rendered file
            await self.connection.put(temp_path, dest, mode=mode)
            
            return ModuleResult(
                changed=True,
                msg=f"Template rendered to {dest}",
                results={
                    "src": src,
                    "dest": dest,
                    "checksum": self._compute_checksum(rendered.encode(output_encoding)),
                },
            )
        finally:
            temp_path.unlink(missing_ok=True)
    
    def _compute_checksum(self, content: bytes) -> str:
        """Compute SHA256 checksum of content."""
        import hashlib
        return hashlib.sha256(content).hexdigest()
