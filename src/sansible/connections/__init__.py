"""
Sansible Connections Module

Connection plugins for SSH and WinRM.
"""

from sansible.connections.base import Connection, RunResult, create_connection_factory
from sansible.connections.local import LocalConnection

__all__ = [
    'Connection',
    'RunResult',
    'LocalConnection',
    'create_connection_factory',
]
