"""
Loaded at interpreter start by sansible_autoload.pth. Installs the compat layer the moment
the first `ansible` module is imported, so the stock ansible-playbook, ansible-galaxy, etc.
work without wrappers. Costs one meta path entry until then; set SANSIBLE_DISABLE=1 to opt out.
"""
from __future__ import annotations

import importlib.abc
import os
import sys


class _Autoload(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name != "ansible" and not name.startswith("ansible."):
            return None
        sys.meta_path.remove(self)
        # modules executed on a POSIX target by the local connection import ansible.module_utils
        if "AnsiballZ_" in os.path.basename(sys.argv[0] if sys.argv else ""):
            return None
        try:
            from sansible._compat import install

            install()
        except Exception as ex:
            print(f"[sansible] failed to load the compatibility layer: {ex}", file=sys.stderr)
        return None


if not os.environ.get("SANSIBLE_DISABLE") and not any(isinstance(f, _Autoload) for f in sys.meta_path):
    sys.meta_path.insert(0, _Autoload())
