"""
Replace ansible-core's fork-per-task WorkerProcess with a thread-per-task worker.

ansible-core asks for multiprocessing.get_context('fork'). Where fork does not exist we
hand back a context whose Process is a thread; queues/locks come from 'spawn' (which
works everywhere). The isolation fork gave for free (a private copy of host/task/vars)
is recreated by cloning those objects at worker start.
"""
from __future__ import annotations

import copy
import multiprocessing
import os
import pickle
import sys
import threading
import traceback

from . import _source_patches

_tls = threading.local()


class ThreadProcess:
    """The subset of multiprocessing.Process that ansible-core uses."""

    _counter = 0

    def __init__(self, *args, **kwargs):
        ThreadProcess._counter += 1
        self.name = f"{type(self).__name__}-{ThreadProcess._counter}"
        self.daemon = True
        self.exitcode = None
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._bootstrap, name=self.name, daemon=True)
        self._thread.start()

    def _bootstrap(self):
        try:
            self.run()
            self.exitcode = 0
        except BaseException:
            self.exitcode = 1
            traceback.print_exc()

    def run(self):
        pass

    @property
    def pid(self):
        return os.getpid()

    def is_alive(self):
        return bool(self._thread and self._thread.is_alive())

    def join(self, timeout=None):
        if self._thread:
            self._thread.join(timeout)

    def terminate(self):
        pass  # threads cannot be killed; workers are daemon threads and die with the process

    kill = terminate

    def close(self):
        pass


class ThreadContext:
    Process = ThreadProcess

    def __init__(self):
        self._spawn = multiprocessing.get_context("spawn")

    def parent_process(self):
        return None if threading.current_thread() is threading.main_thread() else object()

    def __getattr__(self, name):
        return getattr(self._spawn, name)


def _fork_available() -> bool:
    return hasattr(os, "fork")


def _clone(obj):
    """Give the worker its own copy, as fork's copy-on-write used to."""
    try:
        return pickle.loads(pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL))
    except Exception:
        return copy.deepcopy(obj)


def _patch_display(mod):
    Display = mod.Display
    Display._final_q = property(lambda self: getattr(_tls, "final_q", None),
                                lambda self, value: setattr(_tls, "final_q", value))
    Display.set_queue = lambda self, queue: setattr(_tls, "final_q", queue)


class _WorkerSys:
    """worker.py inspects sys.stdout/stderr (StringIO after its fork-side _detach) for stray output."""

    def __getattr__(self, name):
        if name in ("stdout", "stderr"):
            import io
            return getattr(_tls, name, None) or io.StringIO()
        return getattr(sys, name)


def _patch_worker(mod):
    WorkerProcess = mod.WorkerProcess
    mod.sys = _WorkerSys()

    def run(self):
        self._display_queue_set = True
        mod.display.set_queue(self._final_q)
        try:
            self._host = _clone(self._host)
            self._task = _clone(self._task)
            self._task_vars = _clone(self._task_vars)
            self._play_context = _clone(self._play_context)
            with mod._task.TaskContext.create(task=self._task, task_vars=self._task_vars,
                                              host_name=self._host.name):
                return self._run()
        except BaseException:
            mod.display.error(traceback.format_exc())
            raise

    WorkerProcess.run = run


def install() -> None:
    thread_ctx = ThreadContext()
    orig_get_context = multiprocessing.get_context

    def get_context(method=None):
        if method == "fork":
            return thread_ctx
        return orig_get_context(method)

    multiprocessing.get_context = get_context
    _source_patches.POST_IMPORT.setdefault("ansible.utils.display", []).append(_patch_display)
    _source_patches.POST_IMPORT.setdefault("ansible.executor.process.worker", []).append(_patch_worker)
