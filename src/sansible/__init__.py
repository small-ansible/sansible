"""
Sansible: ansible-core that also runs natively on Windows.

Sansible is ansible-core plus a small compatibility layer, loaded automatically at
import time, that removes ansible-core's POSIX-only assumptions:

- task workers run in a persistent pool of spawned processes instead of fork()
- POSIX-only stdlib modules get portable stand-ins
- a handful of '/'-separator and permission-bit assumptions are patched
- `ssh` connections from a Windows controller use a pure-Python (paramiko) plugin

The version is the ansible-core version it is built and tested on, plus a Sansible
revision: 2.22.0.1 is ansible-core 2.22.0, Sansible revision 1.
"""
from __future__ import annotations

__version__ = "2.22.0.1"

ANSIBLE_CORE_VERSION = "2.22.0"
"""The exact ansible-core version this Sansible release patches and is tested against."""
