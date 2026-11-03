"""
Exact-text source patches for ansible-core modules, applied at import time.

Each patch is (old, new). If `old` is not found the import fails loudly, so drift
against a new ansible-core release is detected instead of silently ignored.
"""
from __future__ import annotations

import importlib.abc
import importlib.machinery
import sys

PATCHES: dict[str, list[tuple[str, str]]] = {
    # os.path.sep is a backslash on Windows and must be escaped inside a regex.
    "ansible.parsing.dataloader": [(
        "RE_TASKS = re.compile('(?:^|%s)+tasks%s?$' % (os.path.sep, os.path.sep))",
        "RE_TASKS = re.compile('(?:^|%s)+tasks%s?$' % (re.escape(os.path.sep), re.escape(os.path.sep)))",
    )],
    # No fork on this platform, so there is nothing to re-arm after one.
    "ansible.module_utils._internal._concurrent._fork_safe_lock": [(
        "        _os.register_at_fork(\n",
        "        hasattr(_os, 'register_at_fork') and _os.register_at_fork(\n",
    )],
    "ansible.utils.display": [(
        "        os.register_at_fork(after_in_child=disable_lock)",
        "        hasattr(os, 'register_at_fork') and os.register_at_fork(after_in_child=disable_lock)",
    )],
    # Origin tags assume POSIX absolute paths ('/...'); Windows paths are 'C:\\...'.
    "ansible._internal._datatag._tags": [(
        "if not self.path.startswith('/'):",
        "if not __import__('os').path.isabs(self.path):",
    )],
    # ShellBase describes POSIX targets but used the controller's os.path for remote paths.
    "ansible.plugins.shell": [
        ("        if not all(os.path.isabs(d) for d in normalized_paths):",
         "        if not all(__import__('posixpath').isabs(d) for d in normalized_paths):"),
        ("        return os.path.join(*args)", "        return __import__('posixpath').join(*args)"),
        ("        base_name = os.path.basename(pathname.strip())",
         "        base_name = __import__('posixpath').basename(pathname.strip())"),
    ],
    # Collection loader assumes '/' separators for controller-side paths.
    "ansible.utils.collection_loader._collection_finder": [
        ("        if not path[0] == '/':", "        if not os.path.isabs(path):"),
        ("    path_parts = path.split('/')\n    if path_parts.count('ansible_collections') != 1:",
         "    path_parts = path.replace(os.sep, '/').split('/')\n    if path_parts.count('ansible_collections') != 1:"),
    ],
    # Windows reports every file as world-writable through st_mode (no POSIX permission bits).
    "ansible.config.manager": [
        ("        if perms.st_mode & stat.S_IWOTH:", "        if perms.st_mode & stat.S_IWOTH and os.name != 'nt':"),
    ],
    "ansible.galaxy.api": [
        ("    if cache_mode & stat.S_IWOTH:", "    if cache_mode & stat.S_IWOTH and os.name != 'nt':"),
    ],
}

def _no_sigusr1_debug(mod):
    """SIGUSR1 stack-dump debugging hook; Windows has no SIGUSR1."""
    orig = mod.register_for_stacktrace
    mod.register_for_stacktrace = lambda *a, **k: orig(*a, **k) if hasattr(__import__("signal"), "SIGUSR1") else None


def _posix_module_paths(mod):
    """Module FQNs are derived by regex over the module's file path, assuming '/' separators."""
    import re

    site_packages = mod.site_packages.replace("\\", "/")
    mod.CORE_LIBRARY_PATH_RE = re.compile(r"%s/(?P<path>ansible/modules/.*)\.(py|ps1)$" % re.escape(site_packages))
    orig = mod._get_ansible_module_fqn
    mod._get_ansible_module_fqn = lambda module_path: orig(module_path.replace("\\", "/"))


POST_IMPORT: dict[str, list] = {  # module name -> [callable(module)]
    "ansible.module_utils._internal._debug": [_no_sigusr1_debug],
    "ansible.executor.module_common": [_posix_module_paths],
}


class _Loader(importlib.machinery.SourceFileLoader):
    def __init__(self, fullname, path, patches, hooks):
        super().__init__(fullname, path)
        self._patches, self._hooks = patches, hooks

    def get_code(self, fullname):
        source = self.get_source(fullname)
        for old, new in self._patches:
            if old not in source:
                raise ImportError(f"sansible compat: patch target not found in {fullname}: {old[:60]!r}")
            source = source.replace(old, new, 1)
        return compile(source, self.path, "exec", dont_inherit=True)

    def exec_module(self, module):
        super().exec_module(module)
        for hook in self._hooks:
            hook(module)


class _Finder(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name not in PATCHES and name not in POST_IMPORT:
            return None
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is None or not spec.origin or not spec.origin.endswith(".py"):
            return spec
        spec.loader = _Loader(name, spec.origin, PATCHES.get(name, []), POST_IMPORT.get(name, []))
        return spec


def install() -> None:
    sys.meta_path.insert(0, _Finder())
