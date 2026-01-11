"""
Sansible Galaxy Module Support

Provides support for Ansible Galaxy collections by executing them
remotely via ansible-core on the target host (Strategy A: Remote Execution).

This approach installs ansible-core on the remote host temporarily (or uses
an existing installation), then executes Galaxy modules through ansible's
native module execution, capturing the JSON output.

Benefits:
- Full compatibility with all Galaxy modules
- Modules execute in their native environment
- Complex module dependencies resolved automatically
- No need to port module code

Usage:
    # In playbook, use any Galaxy module:
    - name: Set timezone
      community.general.timezone:
        name: America/New_York

    # Sansible will detect it's a Galaxy module and:
    # 1. Check if ansible-core exists on remote
    # 2. Install if needed (pip install ansible-core)
    # 3. Install the collection (ansible-galaxy collection install)
    # 4. Execute via: ansible localhost -m module -a args --connection local
    # 5. Parse JSON output
"""

from sansible.galaxy.loader import GalaxyModuleLoader, CollectionInfo, GalaxyHostState
from sansible.galaxy.executor import GalaxyModuleExecutor
from sansible.galaxy.module import GalaxyModule, create_galaxy_module
from sansible.galaxy.config import GalaxyConfig, get_config, set_config, configure

__all__ = [
    'GalaxyModuleLoader',
    'GalaxyModuleExecutor', 
    'GalaxyModule',
    'CollectionInfo',
    'GalaxyHostState',
    'GalaxyConfig',
    'get_config',
    'set_config',
    'configure',
    'create_galaxy_module',
]
