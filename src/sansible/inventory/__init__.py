"""
Sansible Inventory Module

Provides inventory parsing and host/group management.
Supports both INI and YAML inventory formats.
"""

from sansible.inventory.parser import InventoryParser
from sansible.inventory.host import Host
from sansible.inventory.group import Group
from sansible.inventory.manager import InventoryManager

__all__ = ['InventoryParser', 'Host', 'Group', 'InventoryManager']
