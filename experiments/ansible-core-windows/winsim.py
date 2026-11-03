"""Make this Linux CPython look like Windows CPython to ansible-core (test harness only)."""
import importlib.abc, multiprocessing, os, signal, sys

BLOCKED = {"fcntl", "termios", "tty", "pty", "pwd", "grp", "resource", "syslog", "posix"}
POSIX_ONLY_OS = ["fork", "forkpty", "register_at_fork", "setsid", "setpgid", "getpgid", "killpg",
                 "getuid", "geteuid", "getgid", "getegid", "getgroups", "chown", "lchown",
                 "mkfifo", "openpty", "uname", "sysconf"]

class _Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name in BLOCKED and name not in sys.modules:
            raise ModuleNotFoundError(f"No module named '{name}' (simulated Windows)")
        return None

for m in BLOCKED:
    sys.modules.pop(m, None)
sys.meta_path.insert(0, _Block())
REMOVED = {n: getattr(os, n) for n in POSIX_ONLY_OS if hasattr(os, n)}
for n in REMOVED:
    delattr(os, n)
for s in ("SIGALRM", "SIGKILL", "SIGHUP"):
    if hasattr(signal, s):
        delattr(signal, s)
if hasattr(signal, "alarm"):
    del signal.alarm

_orig_get_context = multiprocessing.get_context
def _get_context(method=None):
    if method in ("fork", "forkserver"):
        raise ValueError(f"cannot find context for {method!r} (simulated Windows)")
    return _orig_get_context(method)
multiprocessing.get_context = _get_context
