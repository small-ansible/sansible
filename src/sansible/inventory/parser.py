"""
Inventory Parser

Parses INI and YAML inventory files into Host and Group objects.
Pure Python implementation - no external dependencies beyond PyYAML.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

from sansible.inventory.host import Host
from sansible.inventory.group import Group


class InventoryParser:
    """
    Parse inventory files in INI or YAML format.
    
    Supports:
    - INI format (traditional Ansible inventory)
    - YAML format (structured inventory)
    - Host patterns with ranges (e.g., web[01:10].example.com)
    - Inline host variables
    - Group variables via [group:vars]
    - Group children via [group:children]
    """
    
    # Pattern for host range expansion: web[01:10].example.com
    RANGE_PATTERN = re.compile(r'\[(\d+):(\d+)\]')
    # Pattern for INI variable assignment: key=value
    VAR_PATTERN = re.compile(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))')
    
    def __init__(self):
        self.hosts: Dict[str, Host] = {}
        self.groups: Dict[str, Group] = {}
        # Always create 'all' and 'ungrouped' groups
        self.groups['all'] = Group('all')
        self.groups['ungrouped'] = Group('ungrouped')
    
    def parse(self, source: Union[str, Path]) -> Tuple[Dict[str, Host], Dict[str, Group]]:
        """
        Parse an inventory source.
        
        Args:
            source: Path to inventory file, directory, or inline inventory string
            
        Returns:
            Tuple of (hosts dict, groups dict)
        """
        if isinstance(source, str):
            source_path = Path(source)
        else:
            source_path = source
        
        if source_path.is_file():
            self._parse_file(source_path)
        elif source_path.is_dir():
            self._parse_directory(source_path)
        else:
            # Treat as inline inventory string
            self._parse_ini_string(source if isinstance(source, str) else str(source))
        
        # Ensure all hosts are in 'all' group
        for host in self.hosts.values():
            self.groups['all'].add_host(host)
            # If host isn't in any other group, add to 'ungrouped'
            if len(host.groups) == 1 and 'all' in host.groups:
                self.groups['ungrouped'].add_host(host)
        
        return self.hosts, self.groups
    
    def _parse_file(self, path: Path) -> None:
        """Parse a single inventory file."""
        content = path.read_text(encoding='utf-8')
        
        # Detect format by extension or content
        if path.suffix in ('.yml', '.yaml'):
            self._parse_yaml_string(content)
        elif path.suffix == '.json':
            import json
            data = json.loads(content)
            self._parse_yaml_data(data)
        else:
            # Try YAML first (if it looks like YAML)
            if content.strip().startswith(('---', 'all:', 'ungrouped:')):
                try:
                    self._parse_yaml_string(content)
                    return
                except yaml.YAMLError:
                    pass
            # Fall back to INI
            self._parse_ini_string(content)
    
    def _parse_directory(self, path: Path) -> None:
        """Parse all inventory files in a directory."""
        for item in sorted(path.iterdir()):
            if item.is_file() and not item.name.startswith('.'):
                # Skip backup files and non-inventory files
                if item.suffix not in ('.bak', '.orig', '.pyc', '.pyo'):
                    self._parse_file(item)
    
    def _parse_ini_string(self, content: str) -> None:
        """Parse INI format inventory."""
        current_group: Optional[str] = None
        current_section: Optional[str] = None  # 'hosts', 'vars', 'children'
        
        for line_num, line in enumerate(content.splitlines(), 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#') or line.startswith(';'):
                continue
            
            # Check for group header
            if line.startswith('[') and line.endswith(']'):
                header = line[1:-1]
                
                if ':vars' in header:
                    # [group:vars] section
                    group_name = header.replace(':vars', '')
                    current_group = group_name
                    current_section = 'vars'
                    if group_name not in self.groups:
                        self.groups[group_name] = Group(group_name)
                
                elif ':children' in header:
                    # [group:children] section
                    group_name = header.replace(':children', '')
                    current_group = group_name
                    current_section = 'children'
                    if group_name not in self.groups:
                        self.groups[group_name] = Group(group_name)
                
                else:
                    # Regular [group] section
                    current_group = header
                    current_section = 'hosts'
                    if header not in self.groups:
                        self.groups[header] = Group(header)
                
                continue
            
            # Process line based on current section
            if current_section == 'vars':
                # Parse variable assignment
                if '=' in line:
                    key, value = self._parse_variable_line(line)
                    if current_group and key:
                        self.groups[current_group].set_variable(key, value)
            
            elif current_section == 'children':
                # Line is a child group name
                child_name = line.strip()
                if child_name and current_group:
                    if child_name not in self.groups:
                        self.groups[child_name] = Group(child_name)
                    self.groups[current_group].add_child(child_name)
                    self.groups[child_name].add_parent(current_group)
            
            else:
                # Parse host entry (hosts section or no section)
                hosts = self._parse_host_line(line)
                for host in hosts:
                    self.hosts[host.name] = host
                    if current_group:
                        self.groups[current_group].add_host(host)
    
    def _parse_host_line(self, line: str) -> List[Host]:
        """Parse a single host line, handling ranges and variables."""
        parts = line.split()
        if not parts:
            return []
        
        host_pattern = parts[0]
        var_string = ' '.join(parts[1:]) if len(parts) > 1 else ''
        
        # Parse inline variables
        variables = {}
        port = None
        
        for match in self.VAR_PATTERN.finditer(var_string):
            key = match.group(1)
            # Value is in one of the capture groups (quoted or unquoted)
            value = match.group(2) or match.group(3) or match.group(4)
            
            # Handle special ansible_ variables
            if key == 'ansible_port':
                port = int(value)
            else:
                # Try to convert to appropriate type
                variables[key] = self._convert_value(value)
        
        # Expand host patterns (ranges)
        host_names = self._expand_host_pattern(host_pattern)
        
        # Create Host objects
        return [Host(name, port=port, variables=variables) for name in host_names]
    
    def _expand_host_pattern(self, pattern: str) -> List[str]:
        """Expand host patterns like web[01:03].example.com."""
        match = self.RANGE_PATTERN.search(pattern)
        if not match:
            return [pattern]
        
        start = int(match.group(1))
        end = int(match.group(2))
        width = len(match.group(1))  # Preserve leading zeros
        
        results = []
        for i in range(start, end + 1):
            # Replace the pattern with the current number
            num_str = str(i).zfill(width)
            expanded = pattern[:match.start()] + num_str + pattern[match.end():]
            # Recursively expand any remaining patterns
            results.extend(self._expand_host_pattern(expanded))
        
        return results
    
    def _parse_variable_line(self, line: str) -> Tuple[str, Any]:
        """Parse a variable assignment line."""
        if '=' not in line:
            return '', None
        
        key, _, value = line.partition('=')
        key = key.strip()
        value = value.strip()
        
        # Handle quoted values
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        
        return key, self._convert_value(value)
    
    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate Python type."""
        if not isinstance(value, str):
            return value
            
        # Boolean
        if value.lower() in ('true', 'yes'):
            return True
        if value.lower() in ('false', 'no'):
            return False
        
        # None
        if value.lower() in ('null', 'none', '~'):
            return None
        
        # Integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float
        try:
            return float(value)
        except ValueError:
            pass
        
        return value
    
    def _parse_yaml_string(self, content: str) -> None:
        """Parse YAML format inventory."""
        data = yaml.safe_load(content)
        if data:
            self._parse_yaml_data(data)
    
    def _parse_yaml_data(self, data: Dict[str, Any]) -> None:
        """Parse YAML inventory data structure."""
        if not isinstance(data, dict):
            return
        
        # YAML inventory has groups at top level
        for group_name, group_data in data.items():
            self._parse_yaml_group(group_name, group_data or {})
    
    def _parse_yaml_group(self, name: str, data: Dict[str, Any]) -> None:
        """Parse a single group from YAML inventory."""
        if name not in self.groups:
            self.groups[name] = Group(name)
        
        group = self.groups[name]
        
        if not isinstance(data, dict):
            return
        
        # Parse hosts
        hosts_data = data.get('hosts', {})
        if isinstance(hosts_data, dict):
            for host_name, host_vars in hosts_data.items():
                host_vars = host_vars or {}
                port = host_vars.pop('ansible_port', None)
                host = Host(host_name, port=port, variables=host_vars)
                self.hosts[host_name] = host
                group.add_host(host)
        
        # Parse group vars
        vars_data = data.get('vars', {})
        if isinstance(vars_data, dict):
            for key, value in vars_data.items():
                group.set_variable(key, value)
        
        # Parse children (recursive)
        children_data = data.get('children', {})
        if isinstance(children_data, dict):
            for child_name, child_data in children_data.items():
                group.add_child(child_name)
                self._parse_yaml_group(child_name, child_data or {})
                if child_name in self.groups:
                    self.groups[child_name].add_parent(name)
