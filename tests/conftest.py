"""
Tests run against the installed sansible wheel (as users get it), through the real
ansible CLI entry points in separate processes.

Optional environment for remote targets (tests skip without them):
  SANSIBLE_TEST_SSH_HOST / _PORT / _USER / _KEY / _SHELL (sh or powershell)
  SANSIBLE_TEST_PSRP_HOST / _USER / _PASSWORD
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

DATA = Path(__file__).parent / "data"
IS_WINDOWS = sys.platform == "win32"


def ansible_cli(name: str) -> str:
    scripts = Path(sysconfig.get_path("scripts"))
    for candidate in (scripts / name, scripts / f"{name}.exe"):
        if candidate.exists():
            return str(candidate)
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"{name} not found next to {sys.executable}")
    return found


def run_playbook(
    playbook: Path,
    inventory: str,
    *,
    model: str | None = None,
    env: dict[str, str] | None = None,
    args: list[str] | None = None,
    launcher: list[str] | None = None,
    timeout: int = 600,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess:
    full_env = dict(os.environ, ANSIBLE_NOCOLOR="1", ANSIBLE_FORCE_COLOR="0", ANSIBLE_DEPRECATION_WARNINGS="0",
                    PYTHONUTF8="1")
    if model:
        full_env["SANSIBLE_WORKER"] = model
    full_env.update(env or {})
    cmd = (launcher or [ansible_cli("ansible-playbook")]) + ["-i", inventory, str(playbook), *(args or [])]
    proc = subprocess.run(cmd, env=full_env, cwd=cwd or playbook.parent, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")
    proc.args = cmd
    return proc


def recap(output: str) -> dict[str, dict[str, int]]:
    """Parse PLAY RECAP lines into {host: {ok: n, changed: n, ...}}."""
    stats: dict[str, dict[str, int]] = {}
    in_recap = False
    for line in output.splitlines():
        if line.startswith("PLAY RECAP"):
            in_recap = True
            continue
        if in_recap and " : " in line:
            host, _, rest = line.partition(" : ")
            stats[host.strip()] = {k: int(v) for k, v in (kv.split("=") for kv in rest.split())}
    return stats


def assert_ok(proc: subprocess.CompletedProcess) -> dict[str, dict[str, int]]:
    stats = recap(proc.stdout)
    detail = f"\n$ {' '.join(map(str, proc.args))}\n--- stdout ---\n{proc.stdout[-6000:]}\n--- stderr ---\n{proc.stderr[-4000:]}"
    assert proc.returncode == 0, f"exit {proc.returncode}{detail}"
    assert stats, f"no PLAY RECAP{detail}"
    assert all(s.get("failed", 0) == 0 and s.get("unreachable", 0) == 0 for s in stats.values()), detail
    return stats


def write_inventory(path: Path, text: str) -> str:
    path.write_text(text, encoding="utf-8")
    return str(path)


@pytest.fixture
def local_inventory(tmp_path: Path) -> str:
    return write_inventory(tmp_path / "inv.ini", f"localhost ansible_connection=local ansible_python_interpreter={Path(sys.executable).as_posix()}\n")


posix_only = pytest.mark.skipif(IS_WINDOWS, reason="POSIX controller test")
windows_only = pytest.mark.skipif(not IS_WINDOWS, reason="Windows controller test")
