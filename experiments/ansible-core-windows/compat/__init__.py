"""
Prototype compat layer: lets unmodified ansible-core run its controller on a
platform without fork/fcntl/termios/pty/pwd/grp (i.e. Windows).

Must be imported before anything from `ansible`.

SANSIBLE_WORKER selects the worker model:
  fork   - ansible-core's own (default where os.fork exists)
  pool   - persistent pool of spawned worker processes (default without fork)
  thread - thread-per-task workers (first prototype; no process isolation)
"""
from __future__ import annotations

import os

from . import _posix_stubs, _source_patches, _spawn_pool, _threaded_workers

HAS_FORK = hasattr(os, "fork")
WORKER_MODEL = os.environ.get("SANSIBLE_WORKER") or ("fork" if HAS_FORK else "pool")

if not HAS_FORK:
    _posix_stubs.install()
if WORKER_MODEL == "pool":
    _spawn_pool.install()
elif WORKER_MODEL == "thread":
    _threaded_workers.install()
if not HAS_FORK or WORKER_MODEL != "fork":
    _source_patches.install()
