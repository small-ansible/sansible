"""Connection plugins: paramiko ssh (routed from `ssh`), psrp to Windows, and winlocal on a Windows controller."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from conftest import DATA, IS_WINDOWS, assert_ok, run_playbook, windows_only, write_inventory

SSH = {k: os.environ.get(f"SANSIBLE_TEST_SSH_{k.upper()}") for k in ("host", "port", "user", "key", "shell")}
PSRP = {k: os.environ.get(f"SANSIBLE_TEST_PSRP_{k.upper()}") for k in ("host", "user", "password")}
COLLECTIONS = os.environ.get("SANSIBLE_TEST_COLLECTIONS_PATH")  # where ansible.windows is installed


def _env(tmp_path: Path, **extra: str) -> dict[str, str]:
    env = {"HOME": str(tmp_path / "home"), "USERPROFILE": str(tmp_path / "home"),  # isolated known_hosts
           "ANSIBLE_LOCAL_TEMP": str(tmp_path / "ansible-tmp")}
    if COLLECTIONS:
        env["ANSIBLE_COLLECTIONS_PATH"] = COLLECTIONS
    (tmp_path / "home").mkdir(exist_ok=True)
    env.update(extra)
    return env


def _run_twice(play: Path, inv: str, env: dict, args: list[str]):
    first = assert_ok(run_playbook(play, inv, env=env, args=args))
    second = assert_ok(run_playbook(play, inv, env=env, args=args))
    return first, second


def _ssh_inventory(tmp_path: Path, group: str) -> str:
    extra = f"ansible_shell_type={SSH['shell']}" if SSH["shell"] == "powershell" else ""
    return write_inventory(tmp_path / "ssh.ini", "\n".join([
        f"[{group}]",
        f"target ansible_host={SSH['host']} ansible_port={SSH['port'] or 22} ansible_user={SSH['user']} "
        # forward slashes: the INI inventory parser treats backslashes as escapes
        f"ansible_ssh_private_key_file={Path(SSH['key']).as_posix()} ansible_connection=ssh {extra}", "",
    ]))


@pytest.mark.skipif(not SSH["host"], reason="set SANSIBLE_TEST_SSH_* to test ssh")
def test_ssh_via_paramiko(tmp_path):
    windows_target = SSH["shell"] == "powershell"
    if windows_target and not COLLECTIONS:
        pytest.skip("ansible.windows needed (SANSIBLE_TEST_COLLECTIONS_PATH)")
    play = DATA / "windows" / "remote.yml" if windows_target else DATA / "ssh_posix.yml"
    inv = _ssh_inventory(tmp_path, "winremote" if windows_target else "sshposix")
    out_dir = os.environ.get("SANSIBLE_TEST_REMOTE_DIR") or (r"C:\Windows\Temp\sansible-ssh" if windows_target else str(tmp_path / "remote"))
    fetch = tmp_path / "fetched"
    env = _env(tmp_path, SANSIBLE_SSH="paramiko", ANSIBLE_HOST_KEY_CHECKING="True", ANSIBLE_PARAMIKO_HOST_KEY_AUTO_ADD="True")
    first, second = _run_twice(play, inv, env, ["-e", f"out_dir={out_dir}", "-e", f"fetch_dir={fetch.as_posix()}"])
    assert first["target"]["changed"] > second["target"]["changed"]
    assert (fetch / "tmpl.txt").read_text().strip() == "x=a,b"
    assert (tmp_path / "home" / ".ssh" / "known_hosts").exists(), "new host key was not recorded"


@pytest.mark.skipif(not PSRP["host"] or not COLLECTIONS, reason="set SANSIBLE_TEST_PSRP_* and SANSIBLE_TEST_COLLECTIONS_PATH")
def test_psrp_windows_target(tmp_path):
    inv = write_inventory(tmp_path / "psrp.ini", "\n".join([
        "[winremote]",
        f"target ansible_host={PSRP['host']} ansible_user={PSRP['user']} ansible_password={PSRP['password']} "
        "ansible_connection=psrp ansible_psrp_protocol=http ansible_psrp_auth=ntlm ansible_port=5985", "",
    ]))
    fetch = tmp_path / "fetched"
    _, second = _run_twice(DATA / "windows" / "remote.yml", inv, _env(tmp_path),
                               ["-e", r"out_dir=C:\Windows\Temp\sansible-psrp", "-e", f"fetch_dir={fetch.as_posix()}"])
    assert second["target"]["changed"] <= 1  # win_shell always reports changed
    assert (fetch / "tmpl.txt").read_text().strip() == "x=a,b"


@windows_only
@pytest.mark.skipif(not COLLECTIONS, reason="ansible.windows needed (SANSIBLE_TEST_COLLECTIONS_PATH)")
def test_windows_controller_localhost(tmp_path):
    """Implicit localhost on a Windows controller runs through sansible.core.winlocal."""
    inv = write_inventory(tmp_path / "local.ini", "localhost ansible_connection=local\n")
    out_dir = str(tmp_path / "local-out")
    first, second = _run_twice(DATA / "windows" / "local.yml", inv, _env(tmp_path), ["-e", f"out_dir={out_dir}"])
    assert first["localhost"]["changed"] > second["localhost"]["changed"]
    assert Path(out_dir, "tmpl.txt").read_text().strip() == "x=a,b"


@windows_only
def test_python_modules_on_windows_localhost_fail_clearly(tmp_path):
    inv = write_inventory(tmp_path / "local.ini", "localhost ansible_connection=local\n")
    play = tmp_path / "py.yml"
    play.write_text("- hosts: localhost\n  gather_facts: false\n  tasks:\n    - ansible.builtin.command: whoami\n")
    proc = run_playbook(play, inv, env=_env(tmp_path))
    assert proc.returncode != 0
    assert "Traceback" not in proc.stdout + proc.stderr


def test_platform_routing_table():
    from sansible._compat import _routing

    table = _routing.routes()
    if IS_WINDOWS:
        assert table["ssh"] == _routing.PARAMIKO and table["local"] == _routing.WINLOCAL
    elif os.environ.get("SANSIBLE_SSH") != "paramiko":
        assert table == {}
