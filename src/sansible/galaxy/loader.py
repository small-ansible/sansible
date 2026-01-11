"""
Galaxy Module Loader

Handles discovery, installation, and loading of Galaxy collections on remote hosts.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from sansible.connections.base import Connection


# Pattern for Galaxy collection module names
GALAXY_MODULE_PATTERN = re.compile(r'^([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)$')


@dataclass
class CollectionInfo:
    """Information about an Ansible Galaxy collection."""
    namespace: str
    name: str
    version: Optional[str] = None
    path: Optional[str] = None
    installed: bool = False
    
    @property
    def fqcn(self) -> str:
        """Fully Qualified Collection Name."""
        return f"{self.namespace}.{self.name}"
    
    def __str__(self) -> str:
        return f"{self.fqcn}" + (f"=={self.version}" if self.version else "")


@dataclass  
class GalaxyHostState:
    """Tracks Galaxy-related state for a remote host."""
    ansible_installed: Optional[bool] = None
    ansible_version: Optional[str] = None
    ansible_path: Optional[str] = None
    pip_path: Optional[str] = None
    python_path: Optional[str] = None
    installed_collections: Dict[str, CollectionInfo] = field(default_factory=dict)
    pending_collections: Set[str] = field(default_factory=set)


class GalaxyModuleLoader:
    """
    Manages Galaxy module availability on remote hosts.
    
    Handles:
    - Detection of ansible-core installation
    - Installation of ansible-core via pip
    - Collection installation via ansible-galaxy
    - Module discovery
    """
    
    # Cache of host states
    _host_states: Dict[str, GalaxyHostState] = {}
    
    # Minimum required ansible-core version
    MIN_ANSIBLE_VERSION = "2.14.0"
    
    # Built-in collections that don't need to be installed
    BUILTIN_COLLECTIONS = {'ansible.builtin', 'ansible.windows', 'ansible.netcommon', 'ansible.posix'}
    
    def __init__(self, connection: Connection, is_windows: bool = False):
        """
        Initialize loader for a connection.
        
        Args:
            connection: The connection to the remote host
            is_windows: True if target is Windows (uses PowerShell)
        """
        self.connection = connection
        self.is_windows = is_windows
        self.host_key = f"{connection.host.name}"
        
        if self.host_key not in self._host_states:
            self._host_states[self.host_key] = GalaxyHostState()
    
    @property
    def state(self) -> GalaxyHostState:
        """Get the state for this host."""
        return self._host_states[self.host_key]
    
    @staticmethod
    def is_galaxy_module(module_name: str) -> bool:
        """
        Check if a module name is a Galaxy module (has namespace.collection.module format).
        
        Args:
            module_name: The module name to check
            
        Returns:
            True if it's a Galaxy module (FQCN with 3 parts)
        """
        return bool(GALAXY_MODULE_PATTERN.match(module_name))
    
    @staticmethod
    def parse_module_fqcn(module_name: str) -> Tuple[str, str, str]:
        """
        Parse a Galaxy module FQCN into components.
        
        Args:
            module_name: e.g., "community.general.timezone"
            
        Returns:
            Tuple of (namespace, collection, module)
        """
        match = GALAXY_MODULE_PATTERN.match(module_name)
        if not match:
            raise ValueError(f"Invalid Galaxy module name: {module_name}")
        return match.groups()
    
    async def check_ansible_installed(self) -> bool:
        """
        Check if ansible-core is installed on the remote host.
        
        Returns:
            True if ansible-core is available
        """
        if self.state.ansible_installed is not None:
            return self.state.ansible_installed
        
        # Try to find ansible
        if self.is_windows:
            cmd = "python -m pip show ansible-core 2>$null; if ($?) { python -c 'import ansible; print(ansible.__version__)' }"
        else:
            cmd = "python3 -m pip show ansible-core >/dev/null 2>&1 && python3 -c 'import ansible; print(ansible.__version__)' 2>/dev/null || " \
                  "python -m pip show ansible-core >/dev/null 2>&1 && python -c 'import ansible; print(ansible.__version__)' 2>/dev/null || " \
                  "ansible --version 2>/dev/null | head -1"
        
        result = await self.connection.run(cmd)
        
        if result.rc == 0 and result.stdout.strip():
            version_str = result.stdout.strip()
            # Extract version number (e.g., "ansible [core 2.15.0]" -> "2.15.0")
            version_match = re.search(r'(\d+\.\d+\.\d+)', version_str)
            if version_match:
                self.state.ansible_installed = True
                self.state.ansible_version = version_match.group(1)
                return True
        
        self.state.ansible_installed = False
        return False
    
    async def install_ansible(self, upgrade: bool = False) -> bool:
        """
        Install ansible-core on the remote host.
        
        Args:
            upgrade: If True, upgrade existing installation
            
        Returns:
            True if installation succeeded
        """
        # Find python and pip
        await self._find_python()
        
        pip_cmd = self.state.pip_path or "pip3"
        upgrade_flag = "--upgrade" if upgrade else ""
        
        if self.is_windows:
            cmd = f'{pip_cmd} install {upgrade_flag} ansible-core'
        else:
            cmd = f'{pip_cmd} install {upgrade_flag} ansible-core'
        
        result = await self.connection.run(cmd)
        
        if result.rc == 0:
            self.state.ansible_installed = True
            # Re-check version after install
            await self.check_ansible_installed()
            return True
        
        return False
    
    async def ensure_ansible(self) -> bool:
        """
        Ensure ansible-core is installed on the remote host.
        
        Returns:
            True if ansible-core is ready to use
        """
        if await self.check_ansible_installed():
            return True
        
        # Try to install it
        return await self.install_ansible()
    
    async def _find_python(self) -> None:
        """Find python and pip paths on remote."""
        if self.state.python_path:
            return
        
        if self.is_windows:
            # On Windows, assume python is in PATH
            self.state.python_path = "python"
            self.state.pip_path = "pip"
        else:
            # Try python3 first, then python
            for python in ["python3", "python"]:
                result = await self.connection.run(f"which {python} 2>/dev/null")
                if result.rc == 0 and result.stdout.strip():
                    self.state.python_path = result.stdout.strip()
                    self.state.pip_path = f"{python} -m pip"
                    break
    
    async def list_installed_collections(self) -> Dict[str, CollectionInfo]:
        """
        List collections installed on the remote host.
        
        Returns:
            Dict mapping FQCN to CollectionInfo
        """
        if not await self.ensure_ansible():
            return {}
        
        if self.is_windows:
            cmd = "ansible-galaxy collection list --format json 2>$null"
        else:
            cmd = "ansible-galaxy collection list --format json 2>/dev/null"
        
        result = await self.connection.run(cmd)
        
        if result.rc != 0:
            # Fallback to text format
            return await self._list_collections_text()
        
        try:
            data = json.loads(result.stdout)
            collections = {}
            
            # Handle different output formats
            if isinstance(data, dict):
                for path, colls in data.items():
                    if isinstance(colls, dict):
                        for name, info in colls.items():
                            col = CollectionInfo(
                                namespace=name.split('.')[0],
                                name=name.split('.')[1] if '.' in name else name,
                                version=info.get('version'),
                                path=path,
                                installed=True,
                            )
                            collections[col.fqcn] = col
            
            self.state.installed_collections = collections
            return collections
            
        except json.JSONDecodeError:
            return await self._list_collections_text()
    
    async def _list_collections_text(self) -> Dict[str, CollectionInfo]:
        """Parse text format output of ansible-galaxy collection list."""
        cmd = "ansible-galaxy collection list 2>/dev/null"
        result = await self.connection.run(cmd)
        
        collections = {}
        for line in result.stdout.split('\n'):
            # Format: "namespace.name   1.2.3"
            parts = line.split()
            if len(parts) >= 2 and '.' in parts[0]:
                try:
                    namespace, name = parts[0].split('.', 1)
                    col = CollectionInfo(
                        namespace=namespace,
                        name=name,
                        version=parts[1] if len(parts) > 1 else None,
                        installed=True,
                    )
                    collections[col.fqcn] = col
                except ValueError:
                    continue
        
        self.state.installed_collections = collections
        return collections
    
    async def install_collection(
        self,
        collection: str,
        version: Optional[str] = None,
        force: bool = False,
    ) -> bool:
        """
        Install a Galaxy collection on the remote host.
        
        Args:
            collection: Collection FQCN (e.g., "community.general")
            version: Optional version constraint
            force: If True, reinstall even if present
            
        Returns:
            True if installation succeeded
        """
        if not await self.ensure_ansible():
            return False
        
        # Check if already installed
        if not force:
            installed = await self.list_installed_collections()
            if collection in installed:
                return True
        
        # Build install command
        spec = collection
        if version:
            spec = f"{collection}:{version}"
        
        force_flag = "--force" if force else ""
        
        if self.is_windows:
            cmd = f"ansible-galaxy collection install {force_flag} {spec}"
        else:
            cmd = f"ansible-galaxy collection install {force_flag} {spec}"
        
        result = await self.connection.run(cmd)
        
        if result.rc == 0:
            # Update cache
            await self.list_installed_collections()
            return True
        
        return False
    
    async def ensure_collection(self, module_name: str) -> bool:
        """
        Ensure the collection for a module is installed.
        
        Args:
            module_name: Full module name (e.g., "community.general.timezone")
            
        Returns:
            True if collection is available
        """
        if not self.is_galaxy_module(module_name):
            return True  # Not a Galaxy module
        
        namespace, collection, module = self.parse_module_fqcn(module_name)
        fqcn = f"{namespace}.{collection}"
        
        # Built-in collections are always available
        if fqcn in self.BUILTIN_COLLECTIONS:
            return True
        
        # Check if already installed
        installed = self.state.installed_collections
        if fqcn in installed:
            return True
        
        # Refresh list and check again
        installed = await self.list_installed_collections()
        if fqcn in installed:
            return True
        
        # Need to install
        return await self.install_collection(fqcn)
    
    @classmethod
    def reset_cache(cls) -> None:
        """Reset the host state cache."""
        cls._host_states.clear()
