"""
Import-time patching of ansible-core modules.

Two mechanisms, both keyed by module name and applied by one meta path finder:

- PATCHES: exact-text source replacements, applied before the module is compiled.
  If the text is not found the import fails loudly, so drift against a different
  ansible-core release is detected instead of silently running unpatched code.
- POST_IMPORT: callables run with the module object right after it executes.
"""
from __future__ import annotations

import importlib.abc
import importlib.machinery
import importlib.util
import sys
import typing as t

PATCHES: dict[str, list[tuple[str, str]]] = {}
POST_IMPORT: dict[str, list[t.Callable]] = {}

WINDOWS_PATCHES: dict[str, list[tuple[str, str]]] = {
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
    # The collection loader assumes '/' separators for controller-side paths.
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


def _no_sigusr1_debug(mod) -> None:
    """SIGUSR1 stack-dump debugging hook; Windows has no SIGUSR1."""
    orig = mod.register_for_stacktrace
    mod.register_for_stacktrace = lambda *a, **k: orig(*a, **k) if hasattr(__import__("signal"), "SIGUSR1") else None


def _posix_module_paths(mod) -> None:
    """Module FQNs are derived by regex over the module's file path, assuming '/' separators."""
    import re

    site_packages = mod.site_packages.replace("\\", "/")
    mod.CORE_LIBRARY_PATH_RE = re.compile(r"%s/(?P<path>ansible/modules/.*)\.(py|ps1)$" % re.escape(site_packages))
    orig = mod._get_ansible_module_fqn
    mod._get_ansible_module_fqn = lambda module_path: orig(module_path.replace("\\", "/"))


def _plain_str(value):
    return str.__str__(value) if isinstance(value, str) and type(value) is not str else value


def _plain_str_wsman_args(mod) -> None:
    """
    ansible-core's psrp plugin passes data-tagged str subclasses (username, password, ...) to
    pypsrp's WSMan. On Windows, NTLM/Kerberos go through SSPI via sspilib, a Cython extension
    that rejects str subclasses ("Argument 'username' has incorrect type"). Hand it plain strings.
    (Patched here rather than in the psrp plugin: ansible loads plugin files with
    spec_from_file_location, which bypasses import hooks.)
    """
    orig = mod.WSMan.__init__

    def __init__(self, *args, **kwargs):
        orig(self, *[_plain_str(a) for a in args], **{k: _plain_str(v) for k, v in kwargs.items()})

    mod.WSMan.__init__ = __init__


WINDOWS_POST_IMPORT: dict[str, list[t.Callable]] = {
    "ansible.module_utils._internal._debug": [_no_sigusr1_debug],
    "ansible.executor.module_common": [_posix_module_paths],
    "pypsrp.wsman": [_plain_str_wsman_args],
}


class PatchDriftError(ImportError):
    """An ansible-core module no longer contains the text a patch expects."""


def _drift_error(fullname: str, old: str) -> PatchDriftError:
    from sansible import ANSIBLE_CORE_VERSION, __version__

    try:
        from importlib.metadata import version

        found = version("ansible-core")
    except Exception:
        found = "unknown"
    return PatchDriftError(
        f"sansible {__version__} is built for ansible-core {ANSIBLE_CORE_VERSION} but found {found}: "
        f"the patch for {fullname} no longer applies ({old.strip()[:70]!r}). "
        f"Install the matching version with: pip install 'ansible-core=={ANSIBLE_CORE_VERSION}'"
    )


def apply_patches(fullname: str, source: str) -> str:
    for old, new in PATCHES.get(fullname, ()):
        if old not in source:
            raise _drift_error(fullname, old)
        source = source.replace(old, new, 1)
    return source


class _Loader(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        if fullname not in PATCHES:
            return super().get_code(fullname)
        source = apply_patches(fullname, self.get_source(fullname))
        return compile(source, self.path, "exec", dont_inherit=True)

    def exec_module(self, module):
        super().exec_module(module)
        for hook in POST_IMPORT.get(module.__name__, ()):
            hook(module)


class _Finder(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name not in PATCHES and name not in POST_IMPORT:
            return None
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is None or not spec.origin or not spec.origin.endswith(".py"):
            return spec
        spec.loader = _Loader(name, spec.origin)
        return spec


_finder = _Finder()


def register(patches: dict[str, list[tuple[str, str]]], post_import: dict[str, list[t.Callable]]) -> None:
    for name, items in patches.items():
        PATCHES.setdefault(name, []).extend(items)
    for name, hooks in post_import.items():
        POST_IMPORT.setdefault(name, []).extend(hooks)
    already = sorted(n for n in list(patches) + list(post_import) if n in sys.modules)
    if already:
        raise RuntimeError(f"sansible must be loaded before ansible; already imported: {', '.join(already)}")


def install() -> None:
    if _finder not in sys.meta_path:
        sys.meta_path.insert(0, _finder)


def all_patches() -> dict[str, list[tuple[str, str]]]:
    """Registered patches plus the Windows set, which is checked everywhere so drift shows up on any CI platform."""
    merged = {name: list(items) for name, items in WINDOWS_PATCHES.items()}
    for name, items in PATCHES.items():
        merged.setdefault(name, [])
        merged[name] += [item for item in items if item not in merged[name]]
    return merged


def verify() -> list[str]:
    """Check every source patch still applies to the installed ansible-core, without executing the patched modules."""
    problems = []
    for name, items in sorted(all_patches().items()):
        spec = sys.modules[name].__spec__ if name in sys.modules else importlib.util.find_spec(name)
        if spec is None or not spec.origin:
            problems.append(f"{name}: module not found")
            continue
        with open(spec.origin, encoding="utf-8") as f:
            source = f.read()
        problems.extend(f"{name}: missing {old.strip()[:70]!r}" for old, _ in items if old not in source)
    return problems
