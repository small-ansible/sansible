"""
Test harness: make a Linux CPython look like Windows CPython to ansible-core.

Put this directory on PYTHONPATH and set SANSIBLE_TEST_WINSIM=1; every interpreter
(the controller and each spawned worker) then starts without fork, POSIX-only stdlib
modules and POSIX-only os functions, which is what ansible-core meets on Windows.
sys.platform stays 'linux', so Windows-only APIs (msvcrt, taskkill) are not exercised.
"""
import importlib.abc
import multiprocessing
import os
import signal
import sys


def _is_controller_process() -> bool:
    """The ansible CLI and its spawned workers; not modules the local connection runs on this host."""
    if os.environ.get("SANSIBLE_TEST_WINSIM_FORCE") == "1":  # a test's own interpreter
        return True
    prog = os.path.basename(sys.argv[0]) if sys.argv else ""
    return prog.startswith("ansible") or "--multiprocessing-fork" in getattr(sys, "orig_argv", ())


if os.environ.get("SANSIBLE_TEST_WINSIM") == "1" and _is_controller_process():
    # not "posix": it is CPython's own platform module (shutil imports it on 3.14+); Windows has "nt"
    BLOCKED = {"fcntl", "termios", "tty", "pty", "pwd", "grp", "resource", "syslog"}
    # os functions CPython lacks on Windows; stdlib-internal ones (WNOHANG, ...) stay or subprocess breaks
    POSIX_ONLY_OS = ["fork", "forkpty", "register_at_fork", "setsid", "setpgid", "getpgid", "killpg",
                     "getuid", "geteuid", "getgid", "getegid", "getgroups", "chown", "lchown",
                     "mkfifo", "openpty", "uname", "sysconf"]

    class _Block(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path=None, target=None):
            if name in BLOCKED and name not in sys.modules:
                raise ModuleNotFoundError(f"No module named '{name}' (simulated Windows)")
            return None

    for _name in BLOCKED:
        sys.modules.pop(_name, None)
    sys.meta_path.insert(0, _Block())
    for _name in POSIX_ONLY_OS:
        if hasattr(os, _name):
            delattr(os, _name)
    for _sig in ("SIGALRM", "SIGKILL", "SIGHUP", "SIGUSR1"):
        if hasattr(signal, _sig):
            delattr(signal, _sig)
    if hasattr(signal, "alarm"):
        del signal.alarm

    _orig_get_context = multiprocessing.get_context

    def _get_context(method=None):
        if method in ("fork", "forkserver"):
            raise ValueError(f"cannot find context for {method!r} (simulated Windows)")
        return _orig_get_context(method)

    multiprocessing.get_context = _get_context
