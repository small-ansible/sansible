"""
Connection plugin routing for controllers where ansible-core's own plugins cannot work.

On Windows the builtin `ssh` plugin needs OpenSSH ControlPersist, ptys and select() on
pipes, and `local` runs /bin/sh; both are replaced by plugins from the bundled
`sansible.core` collection. SANSIBLE_SSH=paramiko opts in on other platforms.
"""
from __future__ import annotations

import os
import sys

PARAMIKO = "sansible.core.paramiko"
WINLOCAL = "sansible.core.winlocal"


def routes() -> dict[str, str]:
    table: dict[str, str] = {}
    if sys.platform == "win32" or os.environ.get("SANSIBLE_SSH") == "paramiko":
        table.update({"ssh": PARAMIKO, "ansible.builtin.ssh": PARAMIKO, "paramiko": PARAMIKO, "smart": PARAMIKO})
    if sys.platform == "win32":
        table.update({"local": WINLOCAL, "ansible.builtin.local": WINLOCAL})
    return table


def _patch_loader(mod) -> None:
    table = routes()
    loader = mod.connection_loader
    orig = loader.get_with_context

    def get_with_context(name, *args, **kwargs):
        return orig(table.get(name, name), *args, **kwargs)

    loader.get_with_context = get_with_context


def post_import_hooks() -> dict:
    return {"ansible.plugins.loader": [_patch_loader]} if routes() else {}
