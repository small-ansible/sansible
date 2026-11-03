"""
The compatibility layer. `install()` must run before anything from `ansible` is imported;
`sansible._autoload` (loaded by sansible_autoload.pth) arranges that automatically.

Worker models (SANSIBLE_WORKER):
  fork - ansible-core's own fork-per-task workers (default where os.fork exists)
  pool - persistent pool of spawned worker processes (default and required on Windows)
"""
from __future__ import annotations

import os
import sys

HAS_FORK = hasattr(os, "fork")

_state: dict[str, str] = {}


def wanted_worker_model() -> str:
    requested = os.environ.get("SANSIBLE_WORKER", "").strip().lower()
    if not HAS_FORK:
        return "pool"
    return requested if requested in ("fork", "pool") else "fork"


def is_active() -> bool:
    return bool(_state)


def worker_model() -> str:
    return _state.get("worker_model", "fork")


def install(model: str | None = None) -> None:
    """Install the compat layer once. A no-op on POSIX with the default fork model and no opt-ins."""
    if _state:
        return
    from . import _routing, _source_patches

    model = model or wanted_worker_model()
    if not HAS_FORK and model != "pool":
        raise RuntimeError("this platform has no fork(); only the 'pool' worker model is available")

    hooks = _routing.post_import_hooks()
    if model == "fork" and HAS_FORK and not hooks:
        return

    if not HAS_FORK:
        from . import _posix_stubs

        _posix_stubs.install()
        _source_patches.register(_source_patches.WINDOWS_PATCHES, _source_patches.WINDOWS_POST_IMPORT)
    if model == "pool":
        from . import _spawn_pool

        _spawn_pool.install()
    _source_patches.register({}, hooks)
    _source_patches.install()
    _state["worker_model"] = model
    _check_ansible_core_version()


def _check_ansible_core_version() -> None:
    from importlib.metadata import PackageNotFoundError, version

    from sansible import ANSIBLE_CORE_VERSION

    try:
        found = version("ansible-core")
    except PackageNotFoundError:
        return
    if found != ANSIBLE_CORE_VERSION and not os.environ.get("SANSIBLE_ALLOW_VERSION_MISMATCH"):
        print(
            f"[sansible] WARNING: built and tested for ansible-core {ANSIBLE_CORE_VERSION}, found {found}. "
            f"Install the matching version: pip install 'ansible-core=={ANSIBLE_CORE_VERSION}'",
            file=sys.stderr,
        )
