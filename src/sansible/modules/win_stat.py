"""
Sansible win_stat module

Retrieve file or directory status on Windows.
"""

import json
from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WinStatModule(Module):
    """
    Retrieve file or directory status on Windows.
    
    Uses PowerShell to get file information.
    """
    
    name = "win_stat"
    required_args = ["path"]
    optional_args = {
        "get_checksum": True,
        "checksum_algorithm": "sha1",
    }
    
    async def run(self) -> ModuleResult:
        """Get file/directory status on Windows."""
        path = self.args["path"]
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # PowerShell to get file info
        ps_script = f'''
$path = "{path}"
$result = @{{}}

if (Test-Path -LiteralPath $path) {{
    $item = Get-Item -LiteralPath $path -Force
    $result.Exists = $true
    $result.IsDirectory = $item.PSIsContainer
    $result.Length = if ($item.PSIsContainer) {{ 0 }} else {{ $item.Length }}
    $result.Mode = $item.Mode
    $result.LastWriteTime = $item.LastWriteTime.ToString("o")
    $result.CreationTime = $item.CreationTime.ToString("o")
}} else {{
    $result.Exists = $false
}}

$result | ConvertTo-Json -Compress
'''
        
        try:
            result = await self.connection.run(ps_script, shell=True)
            
            if result.rc != 0:
                return ModuleResult(
                    failed=True,
                    msg=f"Failed to stat {path}: {result.stderr}",
                    rc=result.rc,
                )
            
            # Parse JSON output
            stat_data = json.loads(result.stdout.strip())
            
            stat_result = {
                "exists": stat_data.get("Exists", False),
                "path": path,
            }
            
            if stat_data.get("Exists"):
                stat_result.update({
                    "isdir": stat_data.get("IsDirectory", False),
                    "isreg": not stat_data.get("IsDirectory", True),
                    "size": stat_data.get("Length", 0),
                    "mode": stat_data.get("Mode", ""),
                })
            
            return ModuleResult(
                changed=False,
                msg="File stat retrieved",
                results={"stat": stat_result},
            )
        except json.JSONDecodeError as e:
            return ModuleResult(
                failed=True,
                msg=f"Failed to parse stat output: {e}",
            )
        except Exception as e:
            return ModuleResult(
                failed=True,
                msg=f"Failed to stat {path}: {e}",
            )
