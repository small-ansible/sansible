"""
Galaxy Module Executor

Executes Galaxy modules on remote hosts via ansible's native execution.
"""

import json
import re
import shlex
from typing import Any, Dict, Optional

from sansible.connections.base import Connection
from sansible.galaxy.loader import GalaxyModuleLoader


class GalaxyModuleExecutor:
    """
    Executes Galaxy modules on remote hosts.
    
    Uses ansible's native module execution by running:
        ansible localhost -m module.name -a "args" --connection local
    
    This ensures full compatibility with complex modules that have
    dependencies, action plugins, or other special requirements.
    """
    
    def __init__(
        self,
        connection: Connection,
        loader: GalaxyModuleLoader,
        check_mode: bool = False,
        diff_mode: bool = False,
    ):
        """
        Initialize executor.
        
        Args:
            connection: Connection to the remote host
            loader: GalaxyModuleLoader instance
            check_mode: Run in check mode (--check)
            diff_mode: Show diffs (--diff)
        """
        self.connection = connection
        self.loader = loader
        self.check_mode = check_mode
        self.diff_mode = diff_mode
    
    def _build_args_string(self, args: Dict[str, Any]) -> str:
        """
        Convert args dict to ansible module args string.
        
        Args:
            args: Module arguments dict
            
        Returns:
            String suitable for -a argument
        """
        if not args:
            return ""
        
        # For simple key=value args
        parts = []
        for key, value in args.items():
            if isinstance(value, bool):
                parts.append(f"{key}={'yes' if value else 'no'}")
            elif isinstance(value, (list, dict)):
                # Complex values need JSON
                parts.append(f"{key}={json.dumps(value)}")
            elif value is None:
                continue
            else:
                # Escape special characters
                str_val = str(value)
                if ' ' in str_val or '"' in str_val or "'" in str_val:
                    str_val = json.dumps(str_val)
                parts.append(f"{key}={str_val}")
        
        return " ".join(parts)
    
    def _build_command(
        self,
        module_name: str,
        args: Dict[str, Any],
        extra_vars: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build the ansible command to execute the module.
        
        Args:
            module_name: Full module name (e.g., "community.general.timezone")
            args: Module arguments
            extra_vars: Additional variables to pass
            
        Returns:
            Shell command to execute
        """
        parts = ["ansible", "localhost", "-m", module_name]
        
        # Add connection type
        parts.extend(["--connection", "local"])
        
        # Add args
        args_str = self._build_args_string(args)
        if args_str:
            parts.extend(["-a", shlex.quote(args_str)])
        
        # Add extra vars if any
        if extra_vars:
            extra_json = json.dumps(extra_vars)
            parts.extend(["-e", shlex.quote(extra_json)])
        
        # Check mode
        if self.check_mode:
            parts.append("--check")
        
        # Diff mode
        if self.diff_mode:
            parts.append("--diff")
        
        # One-line mode for easier parsing
        parts.extend(["-o"])
        
        return " ".join(parts)
    
    def _build_command_json(
        self,
        module_name: str,
        args: Dict[str, Any],
        extra_vars: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build an ansible-playbook command for JSON output.
        
        Uses a minimal inline playbook for clean JSON output.
        
        Args:
            module_name: Full module name
            args: Module arguments
            extra_vars: Additional variables
            
        Returns:
            Shell command to execute
        """
        # Create a minimal playbook as JSON
        playbook = [{
            "name": "Galaxy module execution",
            "hosts": "localhost",
            "connection": "local",
            "gather_facts": False,
            "tasks": [{
                "name": "Execute module",
                module_name: args,
            }]
        }]
        
        # Write playbook inline using heredoc
        playbook_json = json.dumps(playbook)
        
        # Build command with inline playbook via stdin
        cmd = f"echo {shlex.quote(playbook_json)} | python3 -c 'import sys,yaml,json; print(yaml.dump(json.load(sys.stdin)))' > /tmp/.sansible_galaxy_pb.yml && "
        cmd += "ansible-playbook /tmp/.sansible_galaxy_pb.yml"
        
        if self.check_mode:
            cmd += " --check"
        if self.diff_mode:
            cmd += " --diff"
        
        cmd += " 2>&1"
        
        return cmd
    
    async def execute(
        self,
        module_name: str,
        args: Dict[str, Any],
        extra_vars: Optional[Dict[str, Any]] = None,
        become: bool = False,
        become_user: str = "root",
        become_method: str = "sudo",
    ) -> Dict[str, Any]:
        """
        Execute a Galaxy module on the remote host.
        
        Args:
            module_name: Full module name (e.g., "community.general.timezone")
            args: Module arguments
            extra_vars: Additional variables
            become: Enable privilege escalation
            become_user: User to become
            become_method: Method for privilege escalation
            
        Returns:
            Dict with execution results:
            - changed: bool
            - failed: bool  
            - msg: str
            - stdout: str
            - stderr: str
            - rc: int
            - results: Dict with module-specific output
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
        
        # Build command
        cmd = self._build_command(module_name, args, extra_vars)
        
        # Add become if needed
        if become:
            if become_method == "sudo":
                cmd = f"sudo -u {become_user} {cmd}"
            elif become_method == "su":
                cmd = f"su - {become_user} -c {shlex.quote(cmd)}"
        
        # Execute
        result = await self.connection.run(cmd)
        
        # Parse output
        return self._parse_output(result.stdout, result.stderr, result.rc)
    
    def _parse_output(
        self,
        stdout: str,
        stderr: str,
        rc: int,
    ) -> Dict[str, Any]:
        """
        Parse ansible output into structured result.
        
        Args:
            stdout: Command stdout
            stderr: Command stderr
            rc: Return code
            
        Returns:
            Parsed result dict
        """
        result = {
            "changed": False,
            "failed": rc != 0,
            "msg": "",
            "stdout": stdout,
            "stderr": stderr,
            "rc": rc,
            "results": {},
        }
        
        # Parse ansible output
        # Format: localhost | SUCCESS => {"changed": false, ...}
        # Format: localhost | CHANGED => {"changed": true, ...}
        # Format: localhost | FAILED! => {"changed": false, ...}
        # Note: JSON may span multiple lines
        
        # Try to find JSON in output - look for { and match to }
        # First try to find => marker and extract JSON after it
        arrow_pos = stdout.find('=>')
        if arrow_pos >= 0:
            json_part = stdout[arrow_pos + 2:].strip()
            # Find the opening brace
            brace_start = json_part.find('{')
            if brace_start >= 0:
                # Find matching closing brace
                brace_count = 0
                json_end = brace_start
                for i, char in enumerate(json_part[brace_start:], brace_start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                try:
                    json_str = json_part[brace_start:json_end]
                    parsed = json.loads(json_str)
                    result["changed"] = parsed.get("changed", False)
                    result["failed"] = parsed.get("failed", result["failed"])
                    result["msg"] = parsed.get("msg", "")
                    result["results"] = parsed
                    return result
                except json.JSONDecodeError:
                    pass
        
        # Check for status indicators in output
        if "SUCCESS" in stdout or "CHANGED" in stdout:
            result["failed"] = False
            result["changed"] = "CHANGED" in stdout
        elif "FAILED" in stdout:
            result["failed"] = True
        
        # Extract message from stderr if present
        if stderr:
            result["msg"] = stderr.strip()
        elif not result["msg"] and stdout:
            # Use last non-empty line as message
            lines = [l for l in stdout.strip().split('\n') if l.strip()]
            if lines:
                result["msg"] = lines[-1]
        
        return result
    
    async def execute_json(
        self,
        module_name: str,
        args: Dict[str, Any],
        extra_vars: Optional[Dict[str, Any]] = None,
        become: bool = False,
        become_user: str = "root",
        become_method: str = "sudo",
    ) -> Dict[str, Any]:
        """
        Execute a Galaxy module and return JSON output.
        
        This method uses ansible-playbook with a minimal playbook for
        more reliable JSON output parsing.
        
        Args:
            module_name: Full module name
            args: Module arguments
            extra_vars: Additional variables
            become: Enable privilege escalation
            become_user: User to become
            become_method: Method for privilege escalation
            
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
        
        # Build playbook command
        cmd = self._build_command_json(module_name, args, extra_vars)
        
        # Add become if needed
        if become:
            if become_method == "sudo":
                cmd = f"sudo -u {become_user} sh -c {shlex.quote(cmd)}"
            elif become_method == "su":
                cmd = f"su - {become_user} -c {shlex.quote(cmd)}"
        
        # Execute
        result = await self.connection.run(cmd)
        
        # Parse output
        return self._parse_output(result.stdout, result.stderr, result.rc)
