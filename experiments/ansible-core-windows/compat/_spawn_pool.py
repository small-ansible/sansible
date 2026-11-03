"""
Run ansible-core task workers in a persistent pool of *spawned* processes instead of
forking one process per host per task.

Why it works: a forked worker can never write back into the controller's memory, so
ansible-core already returns everything explicitly (results/display/callbacks over
FinalQueue, inventory changes over the worker->controller RPC). Fork is only used to
hand *inputs* to the worker cheaply. Here the inputs are pickled once per task (about 5 ms
and 150 KiB in measurements), and the controller state that fork used to carry implicitly is
rebuilt once per worker process (`_ControllerState`) or sent with each job (`_JobState`).

Controller side: `PoolWorker` replaces `WorkerProcess` with the same surface the
strategy uses (start / is_alive / exitcode / worker_queue / worker_id).
Worker side: `_worker_main` loops over jobs and runs the original `WorkerProcess._run`.
"""
from __future__ import annotations

import atexit
import dataclasses
import io
import multiprocessing
import multiprocessing.connection
import os
import pickle
import signal
import sys
import threading
import traceback
import typing as t

from . import _source_patches

_SPAWN = multiprocessing.get_context("spawn")


@dataclasses.dataclass
class _ControllerState:
    """Ambient controller state a forked worker inherited; applied once per spawned worker."""

    cliargs: t.Any
    verbosity: int
    collections_path: list
    vault_secrets: t.Any
    rpc_address: t.Any
    rpc_authkey: bytes
    session_isolation: bool

    @classmethod
    def capture(cls) -> "_ControllerState":
        from ansible import constants as C, context
        from ansible._internal import _rpc_host
        from ansible.parsing.vault import VaultSecretsContext
        from ansible.utils.display import Display

        rpc = _rpc_host.LocalManager.shared_instance()
        vault_ctx = VaultSecretsContext.current(optional=True)
        collections_path = context.CLIARGS.get("collections_path") or []
        if isinstance(collections_path, (str, bytes)):
            collections_path = [collections_path]
        return cls(
            cliargs=context.CLIARGS,
            verbosity=Display().verbosity,
            collections_path=list(collections_path),
            vault_secrets=vault_ctx.secrets if vault_ctx else None,
            rpc_address=rpc.address,
            rpc_authkey=bytes(rpc.authkey),
            session_isolation=bool(C.config.get_config_value("WORKER_SESSION_ISOLATION")),
        )

    def apply(self) -> None:
        from ansible import constants as C, context
        from ansible._internal import _rpc_host
        from ansible._internal._secret_input import load_secret_input_files
        from ansible.parsing.vault import VaultSecretsContext
        from ansible.plugins.loader import init_plugin_loader
        from ansible.utils.display import Display

        context.CLIARGS = self.cliargs
        Display().verbosity = self.verbosity
        load_secret_input_files(C.config.get_config_value("_SECRETS_INPUT_FILES"))
        init_plugin_loader(self.collections_path)
        if self.vault_secrets is not None:
            VaultSecretsContext.initialize(VaultSecretsContext(self.vault_secrets))
        # _rpc_host.AutoRegisterRPC.get_client() "assumes the caller was forked from the controller"
        # and reads the server address from the singleton; point it at the controller's server.
        _rpc_host.LocalManager._shared_instance = _RemoteRPCHost(self.rpc_address, self.rpc_authkey)


@dataclasses.dataclass
class _RemoteRPCHost:
    address: t.Any
    authkey: bytes


@dataclasses.dataclass
class _JobState:
    """Controller state that can change during a run; sent with every job (small)."""

    plugin_dirs: list
    playbook_paths: list
    default_collection: t.Any

    @classmethod
    def capture(cls) -> "_JobState":
        from ansible.plugins.loader import get_all_plugin_loaders
        from ansible.utils.collection_loader import AnsibleCollectionConfig

        return cls(
            plugin_dirs=[(name, list(loader._extra_dirs)) for name, loader in get_all_plugin_loaders()],
            # the getter returns '<dir>/collections' but the setter appends 'collections' itself
            playbook_paths=[os.path.dirname(p) for p in AnsibleCollectionConfig.playbook_paths],
            default_collection=AnsibleCollectionConfig.default_collection,
        )

    def apply(self) -> None:
        from ansible.plugins import loader as plugin_loader
        from ansible.utils.collection_loader import AnsibleCollectionConfig

        loaders = dict(plugin_loader.get_all_plugin_loaders())
        for name, dirs in self.plugin_dirs:
            loader = loaders.get(name)
            for d in dirs:
                if loader is not None and d not in loader._extra_dirs:
                    loader.add_directory(d)
        if [os.path.dirname(p) for p in AnsibleCollectionConfig.playbook_paths] != self.playbook_paths:
            AnsibleCollectionConfig.playbook_paths = self.playbook_paths
        AnsibleCollectionConfig.default_collection = self.default_collection


# --------------------------------------------------------------------------- worker side


def _ensure_stdio_fds() -> None:
    """
    A spawned child can start with fd 0-2 closed (ansible's controller stdio is not
    inheritable). Fill them before multiprocessing unpickles our pipes, or the pipes land
    on 0-2 and get clobbered when stdio is redirected.
    """
    for fd in (0, 1, 2):
        try:
            os.fstat(fd)
        except OSError:
            devnull = os.open(os.devnull, os.O_RDWR)
            if devnull != fd:
                os.dup2(devnull, fd)
                os.close(devnull)


def _detach_stdio(session_isolation: bool, keep: set) -> None:
    """Same intent as WorkerProcess._detach(): workers must talk only through Display."""
    if session_isolation and hasattr(os, "setsid"):
        try:
            os.setsid()
        except OSError:
            pass
    for fds, mode in (((0,), os.O_RDWR), ((1, 2), os.O_WRONLY)):
        devnull = os.open(os.devnull, mode)
        for fd in fds:
            if fd not in keep:
                os.dup2(devnull, fd)
        os.close(devnull)


def _conn_fds(*queues) -> set:
    fds = set()
    for q in queues:
        for attr in ("_reader", "_writer"):
            conn = getattr(q, attr, None)
            try:
                fds.add(conn.fileno())
            except (AttributeError, OSError):
                pass
    return fds


def _log_crash() -> None:
    log = os.environ.get("SANSIBLE_POOL_LOG")
    if log:
        with open(log, "a") as f:
            f.write(traceback.format_exc())


def _worker_main(*args) -> None:
    if os.environ.get("SANSIBLE_POOL_LOG"):
        with open(os.environ["SANSIBLE_POOL_LOG"], "a") as f:
            f.write(f"worker {args[0]} started pid={os.getpid()}\n")
    try:
        _worker_loop(*args)
    except BaseException:
        _log_crash()
        raise


def _worker_loop(slot, final_q, job_q, ack_q, response_q, controller_state: _ControllerState) -> None:
    boot_log = os.environ.get("SANSIBLE_BOOT_LOG")
    if boot_log:
        with open(boot_log, "a") as f:
            f.write(f"{os.getpid()} pool-worker slot={slot}\n")
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # the controller owns Ctrl-C and shuts the pool down

    from ansible._internal import _task
    from ansible.executor.process import worker as worker_mod
    from ansible.plugins.loader import get_plugin_loader_namespace
    from ansible.utils.display import Display

    controller_state.apply()
    display = Display()
    display.set_queue(final_q)
    _detach_stdio(controller_state.session_isolation, keep=_conn_fds(final_q, job_q, ack_q, response_q))
    shared_loader_obj = get_plugin_loader_namespace()
    WorkerProcess = worker_mod._ForkWorkerProcess

    while True:
        payload = job_q.get()
        if payload is None:
            return
        task_vars, host, task, play_context, loader, variable_manager, worker_id, job_state = pickle.loads(payload)
        job_state.apply()
        loader._tempfiles = set()

        w = WorkerProcess.__new__(WorkerProcess)  # reuse the real per-task logic, skip Process.__init__
        w.__dict__.update(
            _final_q=final_q, _task_vars=task_vars, _host=host, _task=task, _play_context=play_context,
            _loader=loader, _variable_manager=variable_manager, _shared_loader_obj=shared_loader_obj,
            worker_queue=response_q, worker_id=worker_id, _cliargs=controller_state.cliargs,
            _stacktrace_dir=None,
        )
        sys.stdout, sys.stderr = io.StringIO(), io.StringIO()  # _run() reports stray writes to these
        try:
            with _task.TaskContext.create(task=task, task_vars=task_vars, host_name=host.name):
                w._run()
        except BaseException:
            # like WorkerProcess._hard_exit(): no safe way back; the controller sees a dead worker
            display.error(traceback.format_exc())
            _log_crash()
            os._exit(1)
        ack_q.put(worker_id)


# --------------------------------------------------------------------------- controller side


class _Slot:
    """One long-lived spawned process serving one strategy worker slot."""

    def __init__(self, pool: "_Pool", index: int):
        from ansible.executor.process.worker import WorkerQueue

        self.index = index
        self.job_q = _SPAWN.SimpleQueue()
        self.ack_q = _SPAWN.SimpleQueue()
        self.response_q = WorkerQueue(ctx=_SPAWN)  # prompt responses (strategy -> worker), as before
        self.current: PoolWorker | None = None
        for fd in (0, 1, 2):  # let the worker report bootstrap failures on the controller's stdio
            try:
                os.set_inheritable(fd, True)
            except OSError:
                pass
        self.proc = _SPAWN.Process(
            target=_worker_main,
            args=(index, pool.final_q, self.job_q, self.ack_q, self.response_q, pool.controller_state),
            name=f"ansible-worker-{index}",
            daemon=True,
        )
        self.proc.start()
        self._watcher = threading.Thread(target=self._watch, name=f"ansible-worker-{index}-watch", daemon=True)
        self._watcher.start()

    def _watch(self) -> None:
        reader, sentinel = self.ack_q._reader, self.proc.sentinel
        while True:
            ready = multiprocessing.connection.wait([reader, sentinel])
            if reader in ready:
                self.ack_q.get()
                self._finish(0)
                continue
            self._finish(self.proc.exitcode or 1)  # worker process died
            return

    def _finish(self, exitcode: int) -> None:
        worker, self.current = self.current, None
        if worker is not None:
            worker.exitcode = exitcode
            worker._done.set()

    @property
    def alive(self) -> bool:
        return self.proc.is_alive()

    def submit(self, worker: "PoolWorker", payload: bytes) -> None:
        self.current = worker
        self.job_q.put(payload)

    def stop(self) -> None:
        if self.proc.is_alive():
            try:
                self.job_q.put(None)
            except OSError:
                pass


class _Pool:
    _by_queue: dict[int, "_Pool"] = {}
    _lock = threading.Lock()

    def __init__(self, final_q):
        self.final_q = final_q
        self.controller_state = _ControllerState.capture()
        self.slots: dict[int, _Slot] = {}

    @classmethod
    def for_queue(cls, final_q) -> "_Pool":
        with cls._lock:
            pool = cls._by_queue.get(id(final_q))
            if pool is None:
                pool = cls._by_queue[id(final_q)] = cls(final_q)
            return pool

    def slot(self, index: int) -> _Slot:
        slot = self.slots.get(index)
        if slot is None or not slot.alive:
            slot = self.slots[index] = _Slot(self, index)
        return slot

    def shutdown(self, timeout: float = 5.0) -> None:
        for slot in self.slots.values():
            slot.stop()
        for slot in self.slots.values():
            slot.proc.join(timeout)
            if slot.proc.is_alive():
                slot.proc.terminate()
        self.slots.clear()

    @classmethod
    def shutdown_all(cls) -> None:
        with cls._lock:
            pools, cls._by_queue = list(cls._by_queue.values()), {}
        for pool in pools:
            pool.shutdown()


class PoolWorker:
    """Drop-in for WorkerProcess: same constructor and the surface the strategy/TQM use."""

    def __init__(self, *, final_q, task_vars, host, task, play_context, loader, variable_manager,
                 shared_loader_obj, worker_id, cliargs, stacktrace_dir=None):
        self._args = (task_vars, host, task, play_context, loader, variable_manager)
        self._host, self._task = host, task  # the free strategy reads worker._task._uuid
        self._final_q = final_q
        self.worker_id = worker_id
        self.exitcode = None
        self._done = threading.Event()
        self._started = False
        self._slot = _Pool.for_queue(final_q).slot(worker_id)
        self.worker_queue = self._slot.response_q
        self.name = f"PoolWorker-{worker_id}"

    def start(self) -> None:
        # Snapshot now, exactly when fork would have: the strategy may mutate these objects afterwards.
        payload = pickle.dumps((*self._args, self.worker_id, _JobState.capture()), protocol=pickle.HIGHEST_PROTOCOL)
        self._args = None
        self._started = True
        self._slot.submit(self, payload)

    def is_alive(self) -> bool:
        return self._started and not self._done.is_set()

    def join(self, timeout=None) -> None:
        self._done.wait(timeout)

    @property
    def pid(self):
        return self._slot.proc.pid

    def terminate(self) -> None:
        if self.is_alive():
            self._slot.proc.terminate()

    kill = terminate

    def close(self) -> None:
        pass


def _picklable_role(mod) -> None:
    """Role._hash is a lazily built MappingProxyType cache; drop it when pickling (fork never pickled task inputs)."""

    def __getstate__(self):
        state = self.__dict__.copy()
        state["_hash"] = None
        return state

    mod.Role.__getstate__ = __getstate__


def _rebuild_cache_plugin(name):
    from ansible.plugins.loader import cache_loader

    return cache_loader.get(name)


def _picklable_cache_interposer(mod) -> None:
    """
    Persistent cache plugins are wrapped in a wrapt ObjectProxy, which refuses to pickle.
    Their data lives in an external store, so a worker rebuilds the same plugin from config.
    """

    def __reduce_ex__(self, protocol):
        from ansible import constants as C

        return _rebuild_cache_plugin, (getattr(self.__wrapped__, "_load_name", None) or C.CACHE_PLUGIN,)

    mod.PluginInterposer.__reduce_ex__ = __reduce_ex__


def _patch_worker_module(mod) -> None:
    mod._ForkWorkerProcess = mod.WorkerProcess
    mod.WorkerProcess = PoolWorker


def _patch_tqm(mod) -> None:
    orig_cleanup = mod.TaskQueueManager.cleanup

    def cleanup(self):
        try:
            pool = _Pool._by_queue.pop(id(self._final_q), None)
            if pool:
                pool.shutdown()
        finally:
            orig_cleanup(self)

    mod.TaskQueueManager.cleanup = cleanup


def install() -> None:
    _ensure_stdio_fds()
    orig_get_context = multiprocessing.get_context

    def get_context(method=None):
        # ansible.utils.multiprocessing asks for 'fork'; its queues must be spawn-compatible
        # to be handed to spawned workers.
        return _SPAWN if method == "fork" else orig_get_context(method)

    multiprocessing.get_context = get_context
    _source_patches.POST_IMPORT.setdefault("ansible.executor.process.worker", []).append(_patch_worker_module)
    _source_patches.POST_IMPORT.setdefault("ansible.executor.task_queue_manager", []).append(_patch_tqm)
    _source_patches.POST_IMPORT.setdefault("ansible.playbook.role", []).append(_picklable_role)
    _source_patches.POST_IMPORT.setdefault("ansible._internal._plugins._cache", []).append(_picklable_cache_interposer)
    atexit.register(_Pool.shutdown_all)
