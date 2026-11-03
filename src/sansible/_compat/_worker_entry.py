"""
Entry point of spawned worker processes.

multiprocessing unpickles a Process's target before its arguments, so importing this
module installs the compat layer before any ansible module the arguments refer to
(queues, controller state) gets imported in the worker.
"""
from __future__ import annotations

from . import install

install("pool")


def main(*args) -> None:
    from ._spawn_pool import _worker_main

    _worker_main(*args)
