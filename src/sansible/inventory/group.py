"""
Inventory Group representation.

A Group is a logical collection of hosts.
"""

from typing import Any, Dict, List, Optional, Set

from sansible.inventory.host import Host


class Group:
    """Represents a group of hosts in the inventory."""
    
    def __init__(
        self,
        name: str,
        variables: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a Group.
        
        Args:
            name: Group name
            variables: Group-specific variables
        """
        self.name = name
        self.vars: Dict[str, Any] = variables.copy() if variables else {}
        self._hosts: Dict[str, Host] = {}
        self._children: List[str] = []  # Child group names
        self._parents: List[str] = []   # Parent group names
    
    @property
    def hosts(self) -> List[Host]:
        """Return list of hosts directly in this group."""
        return list(self._hosts.values())
    
    @property
    def host_names(self) -> List[str]:
        """Return list of host names directly in this group."""
        return list(self._hosts.keys())
    
    @property
    def children(self) -> List[str]:
        """Return list of child group names."""
        return self._children.copy()
    
    @property
    def parents(self) -> List[str]:
        """Return list of parent group names."""
        return self._parents.copy()
    
    def add_host(self, host: Host) -> None:
        """Add a host to this group."""
        self._hosts[host.name] = host
        host.add_group(self.name)
    
    def remove_host(self, host_name: str) -> Optional[Host]:
        """Remove a host from this group."""
        return self._hosts.pop(host_name, None)
    
    def has_host(self, host_name: str) -> bool:
        """Check if a host is directly in this group."""
        return host_name in self._hosts
    
    def add_child(self, group_name: str) -> None:
        """Add a child group."""
        if group_name not in self._children:
            self._children.append(group_name)
    
    def add_parent(self, group_name: str) -> None:
        """Record a parent group."""
        if group_name not in self._parents:
            self._parents.append(group_name)
    
    def set_variable(self, key: str, value: Any) -> None:
        """Set a group variable."""
        self.vars[key] = value
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a group variable."""
        return self.vars.get(key, default)
    
    def __repr__(self) -> str:
        return f"Group(name={self.name!r}, hosts={len(self._hosts)}, children={self._children})"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Group):
            return NotImplemented
        return self.name == other.name
    
    def __hash__(self) -> int:
        return hash(self.name)
