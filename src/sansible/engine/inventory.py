"""
Sansible Inventory Manager

Parses and manages inventory from INI files, YAML files, and host/group vars directories.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import yaml

from sansible.engine.errors import InventoryError, ParseError


class Host:
    """Represents a single host in the inventory."""
    
    def __init__(self, name: str, variables: Optional[Dict[str, Any]] = None):
        self.name = name
        self.vars: Dict[str, Any] = variables.copy() if variables else {}
        self._groups: Set[str] = set()
    
    @property
    def ansible_host(self) -> str:
        """Get the actual host to connect to (ansible_host or name)."""
        return self.vars.get('ansible_host', self.name)
    
    @property
    def ansible_port(self) -> int:
        """Get the port number."""
        return int(self.vars.get('ansible_port', 22))
    
    @property
    def ansible_user(self) -> Optional[str]:
        """Get the user to connect as."""
        return self.vars.get('ansible_user')
    
    @property
    def ansible_connection(self) -> str:
        """Get the connection type (ssh, winrm, local)."""
        return self.vars.get('ansible_connection', 'ssh')
    
    @property
    def groups(self) -> List[str]:
        """Return list of group names this host belongs to."""
        return list(self._groups)
    
    def add_group(self, group_name: str) -> None:
        """Add this host to a group."""
        self._groups.add(group_name)
    
    def set_variable(self, key: str, value: Any) -> None:
        """Set a host variable."""
        self.vars[key] = value
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a host variable."""
        return self.vars.get(key, default)
    
    def get_vars(self) -> Dict[str, Any]:
        """Return all host variables including computed ones."""
        result = self.vars.copy()
        result['inventory_hostname'] = self.name
        result['inventory_hostname_short'] = self.name.split('.')[0]
        result['ansible_host'] = self.ansible_host
        return result
    
    def __repr__(self) -> str:
        return f"Host({self.name!r})"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Host):
            return NotImplemented
        return self.name == other.name
    
    def __hash__(self) -> int:
        return hash(self.name)


class Group:
    """Represents a group of hosts."""
    
    def __init__(self, name: str, variables: Optional[Dict[str, Any]] = None):
        self.name = name
        self.vars: Dict[str, Any] = variables.copy() if variables else {}
        self._hosts: Set[str] = set()
        self._children: Set[str] = set()
        self._parents: Set[str] = set()
    
    @property
    def hosts(self) -> List[str]:
        """Return list of host names directly in this group."""
        return list(self._hosts)
    
    @property
    def children(self) -> List[str]:
        """Return list of child group names."""
        return list(self._children)
    
    @property
    def parents(self) -> List[str]:
        """Return list of parent group names."""
        return list(self._parents)
    
    def add_host(self, host_name: str) -> None:
        """Add a host to this group."""
        self._hosts.add(host_name)
    
    def add_child(self, group_name: str) -> None:
        """Add a child group."""
        self._children.add(group_name)
    
    def add_parent(self, group_name: str) -> None:
        """Record a parent group."""
        self._parents.add(group_name)
    
    def set_variable(self, key: str, value: Any) -> None:
        """Set a group variable."""
        self.vars[key] = value
    
    def __repr__(self) -> str:
        return f"Group({self.name!r}, hosts={len(self._hosts)})"


class InventoryManager:
    """
    Manages inventory parsing and host resolution.
    
    Supports:
    - INI format inventory files
    - YAML format inventory files
    - host_vars/ and group_vars/ directories
    - Host patterns for --limit
    """
    
    # Pattern for host range expansion: web[01:10].example.com
    RANGE_PATTERN = re.compile(r'\[(\d+):(\d+)\]')
    # Pattern for INI variable assignment: key=value
    VAR_PATTERN = re.compile(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))')
    
    def __init__(self):
        self.hosts: Dict[str, Host] = {}
        self.groups: Dict[str, Group] = {}
        self._inventory_dir: Optional[Path] = None
        
        # Always create 'all' and 'ungrouped' groups
        self.groups['all'] = Group('all')
        self.groups['ungrouped'] = Group('ungrouped')
    
    def parse(self, source: Union[str, Path]) -> 'InventoryManager':
        """
        Parse an inventory source.
        
        Args:
            source: Path to inventory file or directory
            
        Returns:
            self for chaining
        """
        source_path = Path(source) if isinstance(source, str) else source
        
        if not source_path.exists():
            raise InventoryError(f"Inventory path does not exist: {source_path}")
        
        if source_path.is_file():
            self._inventory_dir = source_path.parent
            self._parse_file(source_path)
        elif source_path.is_dir():
            self._inventory_dir = source_path
            self._parse_directory(source_path)
        else:
            raise InventoryError(f"Invalid inventory source: {source_path}")
        
        # Load host_vars and group_vars
        if self._inventory_dir:
            self._load_vars_directories(self._inventory_dir)
        
        # Ensure all hosts are in 'all' group
        for host_name, host in self.hosts.items():
            self.groups['all'].add_host(host_name)
            host.add_group('all')
            
            # If host isn't in any other explicit group, add to 'ungrouped'
            non_implicit_groups = [g for g in host.groups if g not in ('all', 'ungrouped')]
            if not non_implicit_groups:
                self.groups['ungrouped'].add_host(host_name)
                host.add_group('ungrouped')
        
        return self
    
    def get_hosts(self, pattern: str = "all") -> List[Host]:
        """
        Get hosts matching a pattern.
        
        Supported patterns:
        - "all" - all hosts
        - "group_name" - all hosts in a group (including children)
        - "host_name" - single host
        - "host1,host2" - multiple hosts/groups
        - "group1:&group2" - intersection (basic support)
        - "!group" - exclusion (basic support)
        
        Args:
            pattern: Host pattern string
            
        Returns:
            List of matching Host objects
        """
        if not pattern or pattern == "all":
            return list(self.hosts.values())
        
        # Handle comma-separated patterns
        if ',' in pattern:
            result_hosts: Set[str] = set()
            for sub_pattern in pattern.split(','):
                sub_pattern = sub_pattern.strip()
                if sub_pattern:
                    for host in self.get_hosts(sub_pattern):
                        result_hosts.add(host.name)
            return [self.hosts[name] for name in result_hosts]
        
        # Handle exclusion
        if pattern.startswith('!'):
            exclude_pattern = pattern[1:]
            exclude_names = {h.name for h in self.get_hosts(exclude_pattern)}
            return [h for h in self.hosts.values() if h.name not in exclude_names]
        
        # Handle intersection
        if ':&' in pattern:
            parts = pattern.split(':&')
            if len(parts) == 2:
                hosts1 = {h.name for h in self.get_hosts(parts[0])}
                hosts2 = {h.name for h in self.get_hosts(parts[1])}
                return [self.hosts[name] for name in hosts1 & hosts2]
        
        # Single pattern: check if it's a group or host
        pattern_clean = pattern.strip()
        
        # Check if it's a group
        if pattern_clean in self.groups:
            return self._get_group_hosts_recursive(pattern_clean)
        
        # Check if it's a host
        if pattern_clean in self.hosts:
            return [self.hosts[pattern_clean]]
        
        # No match
        return []
    
    def _get_group_hosts_recursive(self, group_name: str) -> List[Host]:
        """Get all hosts in a group, including from child groups."""
        if group_name not in self.groups:
            return []
        
        group = self.groups[group_name]
        result_names: Set[str] = set(group.hosts)
        
        # Recursively add hosts from child groups
        for child_name in group.children:
            child_hosts = self._get_group_hosts_recursive(child_name)
            result_names.update(h.name for h in child_hosts)
        
        return [self.hosts[name] for name in result_names if name in self.hosts]
    
    def get_host_vars(self, host_name: str) -> Dict[str, Any]:
        """Get all variables for a host (merged from groups and host)."""
        if host_name not in self.hosts:
            return {}
        
        host = self.hosts[host_name]
        merged_vars: Dict[str, Any] = {}
        
        # Get variables from groups (in order: all, then other groups)
        for group_name in ['all'] + [g for g in host.groups if g != 'all']:
            if group_name in self.groups:
                merged_vars.update(self.groups[group_name].vars)
        
        # Host vars override group vars
        merged_vars.update(host.get_vars())
        
        return merged_vars
    
    def _parse_file(self, path: Path) -> None:
        """Parse a single inventory file."""
        content = path.read_text(encoding='utf-8')
        
        # Detect format by extension or content
        if path.suffix in ('.yml', '.yaml'):
            self._parse_yaml_string(content, path)
        elif path.suffix == '.json':
            import json
            data = json.loads(content)
            self._parse_yaml_data(data, path)
        else:
            # Try YAML first (if it looks like YAML)
            if content.strip().startswith(('---', 'all:', 'ungrouped:')):
                try:
                    self._parse_yaml_string(content, path)
                    return
                except yaml.YAMLError:
                    pass
            # Fall back to INI
            self._parse_ini_string(content, path)
    
    def _parse_directory(self, path: Path) -> None:
        """Parse all inventory files in a directory."""
        for item in sorted(path.iterdir()):
            if item.is_file() and not item.name.startswith('.'):
                # Skip backup files, vars dirs, and non-inventory files
                if item.suffix not in ('.bak', '.orig', '.pyc', '.pyo'):
                    if item.name not in ('host_vars', 'group_vars'):
                        self._parse_file(item)
    
    def _load_vars_directories(self, base_path: Path) -> None:
        """Load variables from host_vars/ and group_vars/ directories."""
        # Load group_vars
        group_vars_dir = base_path / 'group_vars'
        if group_vars_dir.is_dir():
            for item in group_vars_dir.iterdir():
                group_name = item.stem
                if item.is_file() and item.suffix in ('.yml', '.yaml'):
                    if group_name not in self.groups:
                        self.groups[group_name] = Group(group_name)
                    vars_data = yaml.safe_load(item.read_text(encoding='utf-8')) or {}
                    for key, value in vars_data.items():
                        self.groups[group_name].set_variable(key, value)
                elif item.is_dir():
                    # Directory with multiple YAML files
                    if group_name not in self.groups:
                        self.groups[group_name] = Group(group_name)
                    for yaml_file in item.glob('*.yml'):
                        vars_data = yaml.safe_load(yaml_file.read_text(encoding='utf-8')) or {}
                        for key, value in vars_data.items():
                            self.groups[group_name].set_variable(key, value)
                    for yaml_file in item.glob('*.yaml'):
                        vars_data = yaml.safe_load(yaml_file.read_text(encoding='utf-8')) or {}
                        for key, value in vars_data.items():
                            self.groups[group_name].set_variable(key, value)
        
        # Load host_vars
        host_vars_dir = base_path / 'host_vars'
        if host_vars_dir.is_dir():
            for item in host_vars_dir.iterdir():
                host_name = item.stem
                if host_name in self.hosts:
                    host = self.hosts[host_name]
                    if item.is_file() and item.suffix in ('.yml', '.yaml'):
                        vars_data = yaml.safe_load(item.read_text(encoding='utf-8')) or {}
                        for key, value in vars_data.items():
                            host.set_variable(key, value)
                    elif item.is_dir():
                        for yaml_file in item.glob('*.yml'):
                            vars_data = yaml.safe_load(yaml_file.read_text(encoding='utf-8')) or {}
                            for key, value in vars_data.items():
                                host.set_variable(key, value)
                        for yaml_file in item.glob('*.yaml'):
                            vars_data = yaml.safe_load(yaml_file.read_text(encoding='utf-8')) or {}
                            for key, value in vars_data.items():
                                host.set_variable(key, value)
    
    def _parse_ini_string(self, content: str, source_path: Optional[Path] = None) -> None:
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
                header = line[1:-1].strip()
                
                if ':vars' in header:
                    group_name = header.replace(':vars', '').strip()
                    current_group = group_name
                    current_section = 'vars'
                    if group_name not in self.groups:
                        self.groups[group_name] = Group(group_name)
                
                elif ':children' in header:
                    group_name = header.replace(':children', '').strip()
                    current_group = group_name
                    current_section = 'children'
                    if group_name not in self.groups:
                        self.groups[group_name] = Group(group_name)
                
                else:
                    current_group = header
                    current_section = 'hosts'
                    if header not in self.groups:
                        self.groups[header] = Group(header)
                
                continue
            
            # Process line based on current section
            if current_section == 'vars':
                if '=' in line:
                    key, value = self._parse_variable_line(line)
                    if current_group and key:
                        self.groups[current_group].set_variable(key, value)
            
            elif current_section == 'children':
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
                        self.groups[current_group].add_host(host.name)
                        host.add_group(current_group)
    
    def _parse_host_line(self, line: str) -> List[Host]:
        """Parse a single host line, handling ranges and variables."""
        parts = line.split()
        if not parts:
            return []
        
        host_pattern = parts[0]
        var_string = ' '.join(parts[1:]) if len(parts) > 1 else ''
        
        # Parse inline variables
        variables: Dict[str, Any] = {}
        
        for match in self.VAR_PATTERN.finditer(var_string):
            key = match.group(1)
            value = match.group(2) or match.group(3) or match.group(4)
            variables[key] = self._convert_value(value)
        
        # Expand host patterns (ranges)
        host_names = self._expand_host_pattern(host_pattern)
        
        return [Host(name, variables=variables) for name in host_names]
    
    def _expand_host_pattern(self, pattern: str) -> List[str]:
        """Expand host patterns like web[01:03].example.com."""
        match = self.RANGE_PATTERN.search(pattern)
        if not match:
            return [pattern]
        
        start = int(match.group(1))
        end = int(match.group(2))
        width = len(match.group(1))
        
        results = []
        for i in range(start, end + 1):
            num_str = str(i).zfill(width)
            expanded = pattern[:match.start()] + num_str + pattern[match.end():]
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
        
        if value.lower() in ('true', 'yes'):
            return True
        if value.lower() in ('false', 'no'):
            return False
        if value.lower() in ('null', 'none', '~'):
            return None
        
        try:
            return int(value)
        except ValueError:
            pass
        
        try:
            return float(value)
        except ValueError:
            pass
        
        return value
    
    def _parse_yaml_string(self, content: str, source_path: Optional[Path] = None) -> None:
        """Parse YAML format inventory."""
        data = yaml.safe_load(content)
        if data:
            self._parse_yaml_data(data, source_path)
    
    def _parse_yaml_data(self, data: Dict[str, Any], source_path: Optional[Path] = None) -> None:
        """Parse YAML inventory data structure."""
        if not isinstance(data, dict):
            return
        
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
                host = Host(host_name, variables=host_vars)
                self.hosts[host_name] = host
                group.add_host(host_name)
                host.add_group(name)
        
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
