"""The spawn worker pool behaves exactly like ansible-core's fork workers."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from conftest import DATA, ansible_cli, assert_ok, posix_only, run_playbook, write_inventory

SUITE = DATA / "suite"
WINSIM_ENV = {"PYTHONPATH": str(Path(__file__).parent / "winsim"), "SANSIBLE_TEST_WINSIM": "1"}


def _suite_inventory(tmp_path: Path) -> str:
    interp = Path(sys.executable).as_posix()
    return write_inventory(tmp_path / "suite.ini", "\n".join([
        "[web]", "h1", "h2", "h3", "[db]", "h4", "h5",
        "[all:vars]", "ansible_connection=local", f"ansible_python_interpreter={interp}", "",
    ]))


def _run_suite(tmp_path: Path, label: str, **kwargs) -> list[str]:
    record = tmp_path / f"{label}.jsonl"
    env = {"ANSIBLE_CALLBACKS_ENABLED": "record", "ANSIBLE_VAULT_PASSWORD_FILE": str(SUITE / "vault_pass.txt"),
           "RECORD_FILE": str(record)}
    env.update(kwargs.pop("env", {}))
    proc = run_playbook(SUITE / "suite.yml", _suite_inventory(tmp_path), env=env, args=["-f", "5"], **kwargs)
    assert proc.returncode in (0, 2), proc.stdout[-4000:] + proc.stderr[-4000:]  # h5 fails on purpose
    lines = sorted(record.read_text(encoding="utf-8").splitlines())
    assert len(lines) > 50, proc.stdout[-4000:]
    return lines


@posix_only
@pytest.mark.parametrize("variant", ["pool", "winsim"])
def test_results_identical_to_fork(tmp_path, variant):
    """vault, roles with custom modules, adjacent plugins, add_host/group_by (RPC), blocks, includes, delegation."""
    baseline = _run_suite(tmp_path, "fork", model="fork")
    if variant == "pool":
        other = _run_suite(tmp_path, variant, model="pool")
    else:  # simulate a Windows controller (no fork, no fcntl/termios/pty/pwd/grp) on this POSIX host
        other = _run_suite(tmp_path, variant, env=WINSIM_ENV)
    assert other == baseline


@posix_only
def test_basic_playbook_pool(tmp_path, local_inventory):
    out = tmp_path / "out"
    out.mkdir()
    args = ["-e", f"out_dir={out.as_posix()}"]
    first = assert_ok(run_playbook(DATA / "basic.yml", local_inventory, model="pool", args=args))
    assert first["localhost"]["changed"] == 3
    second = assert_ok(run_playbook(DATA / "basic.yml", local_inventory, model="pool", args=args))
    assert second["localhost"]["changed"] == 1  # only the command task with changed_when: true
    assert (out / "tmpl.txt").read_text() == "x=a,b\n"


def _descendants(pid: int) -> set[int]:
    found, frontier = set(), {pid}
    while frontier:
        nxt = set()
        for entry in os.listdir("/proc"):
            if entry.isdigit():
                try:
                    ppid = int(Path(f"/proc/{entry}/stat").read_text().rsplit(")", 1)[1].split()[1])
                except OSError:
                    continue
                if ppid in frontier and int(entry) not in found:
                    nxt.add(int(entry))
        found |= nxt
        frontier = nxt
    return found


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="uses /proc")
def test_ctrl_c_stops_workers_and_task_processes(tmp_path):
    inv = write_inventory(tmp_path / "inv.ini", "\n".join(
        ["[all]", "a", "b", "c", "[all:vars]", "ansible_connection=local", f"ansible_python_interpreter={sys.executable}", ""]))
    play = tmp_path / "slow.yml"
    play.write_text("- hosts: all\n  gather_facts: false\n  tasks:\n    - command: sleep 60\n")
    proc = subprocess.Popen([ansible_cli("ansible-playbook"), "-i", inv, str(play)], env=dict(os.environ, SANSIBLE_WORKER="pool"),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    deadline = time.time() + 60
    while time.time() < deadline and not any(
            b"sleep" in Path(f"/proc/{p}/cmdline").read_bytes() for p in _descendants(proc.pid) if Path(f"/proc/{p}").exists()):
        time.sleep(0.5)
    running = _descendants(proc.pid)
    os.killpg(proc.pid, signal.SIGINT)  # what a terminal Ctrl-C does
    out, _ = proc.communicate(timeout=60)
    time.sleep(1)
    survivors = [p for p in running if Path(f"/proc/{p}").exists()]
    for p in survivors:
        os.kill(p, signal.SIGKILL)
    assert proc.returncode == 99, out.decode()[-2000:]
    assert not survivors, f"processes left behind: {survivors}"


def test_record_callback_parses(tmp_path):
    """Guard the test harness itself: the record callback writes one JSON object per line."""
    rec = tmp_path / "r.jsonl"
    rec.write_text('{"a": 1}\n')
    assert [json.loads(line) for line in rec.read_text().splitlines()] == [{"a": 1}]
