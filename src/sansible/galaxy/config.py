"""
Galaxy Configuration

Settings and configuration for Galaxy module support.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class GalaxyConfig:
    """
    Configuration for Galaxy module execution.
    
    Attributes:
        enabled: Whether Galaxy module support is enabled
        auto_install_ansible: Automatically install ansible-core if missing
        auto_install_collections: Automatically install missing collections
        collection_requirements: List of collections to pre-install
        pip_extra_args: Extra arguments for pip install
        galaxy_extra_args: Extra arguments for ansible-galaxy
        cache_timeout: Seconds to cache collection list (0 = no cache)
    """
    
    enabled: bool = True
    auto_install_ansible: bool = True
    auto_install_collections: bool = True
    collection_requirements: List[str] = field(default_factory=list)
    pip_extra_args: str = ""
    galaxy_extra_args: str = ""
    cache_timeout: int = 300  # 5 minutes
    
    # Performance settings
    parallel_installs: bool = False  # Install collections in parallel
    skip_verification: bool = False  # Skip collection verification
    
    # Advanced settings
    ansible_config: Optional[str] = None  # Path to ansible.cfg on remote
    collections_path: Optional[str] = None  # Custom collections path
    
    # Module allow/deny lists
    allowed_namespaces: Set[str] = field(default_factory=set)  # Empty = allow all
    denied_modules: Set[str] = field(default_factory=set)
    
    def is_module_allowed(self, module_name: str) -> bool:
        """Check if a module is allowed by policy."""
        if module_name in self.denied_modules:
            return False
        
        if not self.allowed_namespaces:
            return True  # No restrictions
        
        # Check namespace
        parts = module_name.split('.')
        if len(parts) >= 2:
            namespace = parts[0]
            return namespace in self.allowed_namespaces
        
        return True


# Default configuration
_config = GalaxyConfig()


def get_config() -> GalaxyConfig:
    """Get the current Galaxy configuration."""
    return _config


def set_config(config: GalaxyConfig) -> None:
    """Set the Galaxy configuration."""
    global _config
    _config = config


def configure(**kwargs) -> None:
    """Configure Galaxy settings."""
    global _config
    for key, value in kwargs.items():
        if hasattr(_config, key):
            setattr(_config, key, value)
