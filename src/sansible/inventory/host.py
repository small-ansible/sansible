"""
Inventory Host representation.

A Host is a target machine that Sansible can manage.
"""

from typing import Any, Dict, Optional, List


class Host:
    """Represents a single host in the inventory."""
    
    def __init__(
        self,
        name: str,
        port: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a Host.
        
        Args:
            name: Hostname or IP address
            port: Optional port number for connections
            variables: Host-specific variables
        """
        self.name = name
        self.port = port
        self.vars: Dict[str, Any] = variables.copy() if variables else {}
        self._groups: List[str] = []
    
    @property
    def groups(self) -> List[str]:
        """Return list of group names this host belongs to."""
        return self._groups.copy()
    
    def add_group(self, group_name: str) -> None:
        """Add this host to a group."""
        if group_name not in self._groups:
            self._groups.append(group_name)
    
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
        if self.port:
            result['ansible_port'] = self.port
        return result
    
    def __repr__(self) -> str:
        return f"Host(name={self.name!r}, port={self.port}, vars={self.vars})"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Host):
            return NotImplemented
        return self.name == other.name
    
    def __hash__(self) -> int:
        return hash(self.name)
