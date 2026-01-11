"""
Windows Galaxy Module Executor

Specialized executor for running Galaxy modules on Windows targets.
Uses PowerShell for all operations.
"""

import json
import re
from typing import Any, Dict, Optional

from sansible.connections.base import Connection
from sansible.galaxy.loader import GalaxyModuleLoader


class WindowsGalaxyExecutor:
    """
    Executes Galaxy modules on Windows hosts via PowerShell.
    
    Windows execution is more complex because:
    - Python may not be in PATH
    - ansible-core needs pip install
    - Path handling is different
    """
    
    def __init__(
        self,
        connection: Connection,
        loader: GalaxyModuleLoader,
        check_mode: bool = False,
        diff_mode: bool = False,
    ):
        """
        Initialize Windows executor.
        
        Args:
            connection: WinRM connection to the remote host
            loader: GalaxyModuleLoader instance
            check_mode: Run in check mode
            diff_mode: Show diffs
        """
        self.connection = connection
        self.loader = loader
        self.check_mode = check_mode
        self.diff_mode = diff_mode
        self._python_path: Optional[str] = None
    
    async def _find_python(self) -> str:
        """Find Python executable on Windows."""
        if self._python_path:
            return self._python_path
        
        # Try common Python locations
        check_paths = [
            "python",  # In PATH
            "py -3",   # Python launcher
            "$env:LOCALAPPDATA\\Programs\\Python\\Python312\\python.exe",
            "$env:LOCALAPPDATA\\Programs\\Python\\Python311\\python.exe",
            "$env:LOCALAPPDATA\\Programs\\Python\\Python310\\python.exe",
            "C:\\Python312\\python.exe",
            "C:\\Python311\\python.exe",
            "C:\\Python310\\python.exe",
        ]
        
        for path in check_paths:
            cmd = f'{path} --version 2>$null; if ($?) {{ Write-Output "{path}" }}'
            result = await self.connection.run(cmd)
            if result.rc == 0 and result.stdout.strip():
                # Extract the working path
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    self._python_path = lines[-1].strip()
                else:
                    self._python_path = path
                return self._python_path
        
        # Default to just "python" and hope for the best
        self._python_path = "python"
        return self._python_path
    
    def _build_args_json(self, args: Dict[str, Any]) -> str:
        """Convert args to JSON string for PowerShell."""
        return json.dumps(args).replace('"', '`"')
    
    async def execute(
        self,
        module_name: str,
        args: Dict[str, Any],
        extra_vars: Optional[Dict[str, Any]] = None,
        become: bool = False,
        become_user: str = "Administrator",
        become_method: str = "runas",
    ) -> Dict[str, Any]:
        """
        Execute a Galaxy module on Windows.
        
        Args:
            module_name: Full module name
            args: Module arguments
            extra_vars: Additional variables
            become: Enable privilege escalation (limited on Windows)
            become_user: User to run as
            become_method: Escalation method (runas)
            
        Returns:
            Execution results dict
        """
        # Ensure collection is installed
        if not await self.loader.ensure_collection(module_name):
            return {
                "changed": False,
                "failed": True,
                "msg": f"Failed to install collection for {module_name}",
                "stdout": "",
                "stderr": "",
                "rc": 1,
                "results": {},
            }
        
        # Find Python
        python = await self._find_python()
        
        # Build args string
        args_json = json.dumps(args)
        
        # Create a temporary playbook file
        playbook_content = f"""---
- name: Galaxy module execution
  hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: Execute module
      {module_name}:
"""
        # Add args to playbook
        for key, value in args.items():
            if isinstance(value, str):
                playbook_content += f'        {key}: "{value}"\n'
            else:
                playbook_content += f'        {key}: {json.dumps(value)}\n'
        
        # Escape for PowerShell
        playbook_escaped = playbook_content.replace("'", "''")
        
        # PowerShell script to execute
        ps_script = f'''
$playbook = @'
{playbook_content}
'@

$tempFile = [System.IO.Path]::GetTempPath() + "sansible_galaxy_" + [guid]::NewGuid().ToString() + ".yml"
$playbook | Out-File -FilePath $tempFile -Encoding UTF8

try {{
    $checkFlag = ""
    $diffFlag = ""
    {"$checkFlag = '--check'" if self.check_mode else ""}
    {"$diffFlag = '--diff'" if self.diff_mode else ""}
    
    $result = & ansible-playbook $tempFile $checkFlag $diffFlag -v 2>&1
    $exitCode = $LASTEXITCODE
    
    Write-Output "EXIT_CODE:$exitCode"
    Write-Output "OUTPUT_START"
    $result | ForEach-Object {{ Write-Output $_ }}
    Write-Output "OUTPUT_END"
}}
finally {{
    Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue
}}
'''
        
        # Execute
        result = await self.connection.run(ps_script)
        
        # Parse output
        return self._parse_output(result.stdout, result.stderr, result.rc)
    
    def _parse_output(
        self,
        stdout: str,
        stderr: str,
        rc: int,
    ) -> Dict[str, Any]:
        """Parse PowerShell output into structured result."""
        result = {
            "changed": False,
            "failed": rc != 0,
            "msg": "",
            "stdout": stdout,
            "stderr": stderr,
            "rc": rc,
            "results": {},
        }
        
        # Extract exit code from output
        exit_match = re.search(r'EXIT_CODE:(\d+)', stdout)
        if exit_match:
            result["rc"] = int(exit_match.group(1))
            result["failed"] = result["rc"] != 0
        
        # Extract output section
        output_match = re.search(r'OUTPUT_START\s*(.*?)\s*OUTPUT_END', stdout, re.DOTALL)
        if output_match:
            output = output_match.group(1)
            
            # Check for status indicators
            if "changed=1" in output or "changed: [" in output:
                result["changed"] = True
            if "ok=1" in output or "ok: [" in output:
                result["failed"] = False
            if "failed=1" in output or "fatal:" in output:
                result["failed"] = True
            
            # Try to extract JSON from output
            json_match = re.search(r'=>\s*(\{[^{}]+\})', output)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(1))
                    result["results"] = parsed
                    result["changed"] = parsed.get("changed", result["changed"])
                    result["msg"] = parsed.get("msg", "")
                except json.JSONDecodeError:
                    pass
        
        # Use stderr for message if available
        if stderr and not result["msg"]:
            result["msg"] = stderr.strip()
        
        return result
