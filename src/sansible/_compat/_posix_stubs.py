"""Stand-ins for POSIX-only stdlib modules/functions that ansible-core imports at module level."""
from __future__ import annotations

import collections
import getpass
import os
import sys
import threading
import types

_USER = getpass.getuser() if "pwd" not in sys.modules else None
_FAKE_UID = 1000


def _module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__dict__.update(attrs)
    mod.__dict__["__sansible_stub__"] = True
    return mod


def _fcntl() -> types.ModuleType:
    try:
        import msvcrt  # real Windows: byte-range locks on the file
    except ImportError:
        msvcrt = None
    _fallback = threading.RLock()  # in-process only; enough for a single controller process

    def lockf(f, op, *a):
        fd = f if isinstance(f, int) else f.fileno()
        if msvcrt:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK if op == LOCK_UN else msvcrt.LK_LOCK, 1)
        elif op == LOCK_UN:
            _fallback.release()
        else:
            _fallback.acquire()

    def fcntl(fd, cmd, arg=0):
        os.fstat(fd if isinstance(fd, int) else fd.fileno())  # raises OSError for a bad fd, like the real one
        return 0

    def ioctl(*a, **k):
        raise OSError("ioctl is not supported on this platform")

    LOCK_SH, LOCK_EX, LOCK_NB, LOCK_UN = 1, 2, 4, 8
    return _module("fcntl", lockf=lockf, flock=lockf, fcntl=fcntl, ioctl=ioctl,
                   LOCK_SH=LOCK_SH, LOCK_EX=LOCK_EX, LOCK_NB=LOCK_NB, LOCK_UN=LOCK_UN,
                   F_GETFD=1, F_SETFD=2, F_GETFL=3, F_SETFL=4, FD_CLOEXEC=1)


def _termios() -> types.ModuleType:
    class error(Exception):
        pass

    def _unsupported(*a, **k):
        raise error("termios is not supported on this platform")

    consts = {n: i for i, n in enumerate(
        "TCSANOW TCSADRAIN TCSAFLUSH TCIFLUSH BRKINT ICRNL INPCK ISTRIP IXON OPOST CSIZE PARENB "
        "CS8 ECHO ICANON IEXTEN ISIG VMIN VTIME VINTR TIOCGWINSZ".split(), start=1)}
    return _module("termios", error=error, tcgetattr=_unsupported, tcsetattr=_unsupported,
                   tcflush=_unsupported, **consts)


def _tty() -> types.ModuleType:
    return _module("tty", IFLAG=0, OFLAG=1, CFLAG=2, LFLAG=3, ISPEED=4, OSPEED=5, CC=6,
                   setraw=lambda *a, **k: None, setcbreak=lambda *a, **k: None)


def _pty() -> types.ModuleType:
    def openpty():
        raise OSError("pty is not supported on this platform")
    return _module("pty", openpty=openpty)


struct_passwd = collections.namedtuple("struct_passwd", "pw_name pw_passwd pw_uid pw_gid pw_gecos pw_dir pw_shell")
uname_result = collections.namedtuple("uname_result", "sysname nodename release version machine")
struct_group = collections.namedtuple("struct_group", "gr_name gr_passwd gr_gid gr_mem")


def _pwd() -> types.ModuleType:
    def _me():
        return struct_passwd(getpass.getuser(), "x", _FAKE_UID, _FAKE_UID, "", os.path.expanduser("~"), "")

    def getpwuid(uid):
        if uid == _FAKE_UID:
            return _me()
        raise KeyError(f"getpwuid(): uid not found: {uid}")

    def getpwnam(name):
        if name == getpass.getuser():
            return _me()
        raise KeyError(f"getpwnam(): name not found: {name!r}")

    return _module("pwd", getpwuid=getpwuid, getpwnam=getpwnam, getpwall=lambda: [_me()],
                   struct_passwd=struct_passwd)


def _grp() -> types.ModuleType:
    def getgrgid(gid):
        raise KeyError(f"getgrgid(): gid not found: {gid}")

    def getgrnam(name):
        raise KeyError(f"getgrnam(): name not found: {name!r}")

    return _module("grp", getgrgid=getgrgid, getgrnam=getgrnam, getgrall=lambda: [],
                   struct_group=struct_group)


def _resource() -> types.ModuleType:
    return _module("resource", RLIMIT_NOFILE=7, getrlimit=lambda r: (8192, 8192),
                   setrlimit=lambda r, v: None)


_STUBS = {"fcntl": _fcntl, "termios": _termios, "tty": _tty, "pty": _pty,
          "pwd": _pwd, "grp": _grp, "resource": _resource}

_OS_STUBS = {
    "getuid": lambda: _FAKE_UID, "geteuid": lambda: _FAKE_UID,
    "getgid": lambda: _FAKE_UID, "getegid": lambda: _FAKE_UID,
    "getgroups": lambda: [_FAKE_UID],
    "uname": lambda: uname_result("Windows", __import__("socket").gethostname(), "", "", ""),
}


class _PyLibc:
    """ansible.utils.display loads libc for wcwidth/wcswidth; Windows has neither."""

    class _Fn:
        def __init__(self, fn):
            self._fn, self.argtypes, self.restype = fn, None, None

        def __call__(self, *a):
            return self._fn(*a)

    def __init__(self):
        import unicodedata

        def wcwidth(c):
            if unicodedata.combining(c) or c in "​‌‍":
                return 0
            if not c.isprintable():
                return -1
            return 2 if unicodedata.east_asian_width(c) in "WF" else 1

        def wcswidth(s, n):
            total = 0
            for c in s[:n]:
                w = wcwidth(c)
                if w < 0:
                    return -1
                total += w
            return total

        self.wcwidth, self.wcswidth = self._Fn(wcwidth), self._Fn(wcswidth)


_LIBC_SENTINEL = "sansible-pylibc"


def _patch_ctypes_libc() -> None:
    import ctypes
    import ctypes.util

    orig_find, orig_load = ctypes.util.find_library, ctypes.cdll.LoadLibrary
    ctypes.util.find_library = lambda name: _LIBC_SENTINEL if name == "c" else orig_find(name)
    ctypes.cdll.LoadLibrary = lambda name: _PyLibc() if name == _LIBC_SENTINEL else orig_load(name)


def _patch_get_blocking() -> None:
    """ansible.cli checks os.get_blocking() on stdio at import; on Windows that raises for console/pipe handles."""
    orig = os.get_blocking

    def get_blocking(fd):
        try:
            return orig(fd)
        except OSError:
            return True  # Windows handles are blocking unless opened overlapped

    os.get_blocking = get_blocking


def _patch_locale() -> None:
    """ansible.cli requires a UTF-8 locale; the Windows default is the ANSI code page (e.g. cp1252)."""
    import locale

    orig = locale.setlocale

    def setlocale(category, value=None):
        if value == "":
            try:
                return orig(category, ".UTF-8")  # UCRT supports UTF-8 locales since Windows 10 1803
            except locale.Error:
                pass
        return orig(category, value)

    locale.setlocale = setlocale
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def install() -> None:
    if not hasattr(os, "fork"):
        _patch_ctypes_libc()
        _patch_get_blocking()
        if sys.platform == "win32":
            _patch_locale()
    for name, factory in _STUBS.items():
        try:
            __import__(name)
        except ImportError:
            sys.modules[name] = factory()
    for name, fn in _OS_STUBS.items():
        if not hasattr(os, name):
            setattr(os, name, fn)
