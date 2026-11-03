# Sansible

**ansible-core that also runs natively on Windows.** No WSL, no Cygwin, no fork of Ansible's
code: `pip install sansible` gives you the real, unmodified ansible-core, plus a small layer
that is loaded automatically at import time and removes ansible-core's POSIX-only assumptions.

```bash
pip install sansible
sansible doctor          # checks the installation
ansible-playbook -i inventory.ini site.yml
```

All the usual commands work: `ansible-playbook`, `ansible`, `ansible-galaxy`,
`ansible-vault`, `ansible-inventory`, `ansible-doc`, and so on. They are ansible-core's own.
Every collection works too.

| Controller | What Sansible changes |
|---|---|
| **Windows** | Everything below is active automatically. |
| Linux / macOS | Nothing, unless you opt in: by default this is plain ansible-core. `SANSIBLE_WORKER=pool` enables the spawn-based worker pool, and `SANSIBLE_SSH=paramiko` routes `ssh` to the pure-Python plugin. |

## What it does

ansible-core's controller assumes a POSIX host. Sansible removes those assumptions without
changing a line of ansible-core on disk:

- **Spawn-based worker pool instead of `fork()`.** ansible-core forks one process per host per
  task; Windows has no `fork()`. Sansible runs tasks in a persistent pool of spawned worker
  processes. Each task's inputs are pickled when ansible-core would have forked, and the
  controller state fork used to carry implicitly is rebuilt explicitly. The result is
  verified identical to fork, using ansible-core's own integration tests.
- **Pure-Python SSH.** The builtin `ssh` plugin needs OpenSSH ControlPersist, ptys and POSIX
  file descriptors. On Windows, `ansible_connection=ssh` is routed to
  `sansible.core.paramiko`, based on ansible-core's own paramiko plugin (removed upstream in
  2026). Inventory variables such as `ansible_user`, `ansible_port`,
  `ansible_ssh_private_key_file` and `ansible_password` work as usual.
- **Windows-local execution.** `connection: local`, implicit `localhost` and
  `delegate_to: localhost` run through `sansible.core.winlocal`, which uses PowerShell, so
  `ansible.windows.*` modules can manage the controller itself.
- **Portable stand-ins** for `fcntl`, `termios`, `pty`, `pwd`, `grp` and libc `wcwidth`.
- **A dozen exact-text patches**, applied at import time, for places where ansible-core
  assumes `/` path separators or POSIX permission bits. If ansible-core ever changes one of
  those lines, the import fails loudly instead of running unpatched code.

## Supported setups

| From a Windows controller to… | Connection | Status |
|---|---|---|
| Windows hosts | `psrp` / `winrm` | ✅ tested (PSRP, including Kerberos/NTLM with your logon credentials) |
| Linux / Unix hosts | `ssh` (paramiko) | ✅ tested |
| Windows hosts over SSH | `ssh` + `ansible_shell_type=powershell` | ✅ tested |
| The Windows controller itself | `local` / implicit `localhost` | ✅ PowerShell modules (`ansible.windows.*`) and controller-side actions |

**Limitations on a Windows controller**

- Python modules (`ansible.builtin.copy`, `command`, …) can't run *on the Windows controller
  itself*; use the `ansible.windows` equivalents for localhost tasks. They work as usual on
  POSIX targets.
- `become` on the local connection isn't supported. Run Ansible from an elevated prompt
  instead.
- Network appliances that need `ansible.netcommon` persistent connections are untested.

## Versions

A Sansible version is the ansible-core version it ships and was tested with, plus a
revision. For example, `2.22.0.1` is ansible-core 2.22.0, Sansible revision 1.

- **ansible-core is pinned exactly.** The import-time patches are verified against that
  release only.
- **New ansible-core releases are tracked automatically.** Every day a GitHub Actions job
  checks PyPI. When a new ansible-core is out, it runs the full test matrix (Linux, macOS and
  Windows; Python 3.13 and 3.14; real SSH and PSRP targets; ansible-core's own integration
  tests under the spawn pool). If everything passes, it publishes the matching Sansible
  release. If anything fails, it opens an issue and publishes nothing.
- **Python 3.13 or newer** is required, the same as ansible-core 2.22.

## Checking an installation

```text
$ sansible doctor
sansible         2.22.0.1
ansible-core     2.22.0 (built for 2.22.0)
worker model     pool
source patches   12 checked (12 active here), all apply
connection       ssh -> sansible.core.paramiko
connection       local -> sansible.core.winlocal
...
OK
```

| Environment variable | Effect |
|---|---|
| `SANSIBLE_WORKER=pool` / `fork` | Worker model. Default: `fork` where available, `pool` on Windows. |
| `SANSIBLE_SSH=paramiko` | Use the pure-Python SSH plugin on Linux/macOS too. |
| `SANSIBLE_DISABLE=1` | Don't load the compatibility layer (Linux/macOS only; Windows needs it). |
| `SANSIBLE_DEBUG_LOG=path` | Log worker starts and crashes. |

## Development

```bash
uv build
uv venv --python 3.13 && uv pip install dist/*.whl pytest pexpect
cd tests && ../.venv/bin/python -m pytest -v
```

Tests run against the installed wheel, through the real ansible CLI. Remote-target tests are
driven by environment variables (`SANSIBLE_TEST_SSH_*`, `SANSIBLE_TEST_PSRP_*`); CI sets
them up with real OpenSSH and WinRM services. `tests/winsim` simulates a Windows controller
on Linux (no fork, no POSIX-only modules) for fast iteration.

Releasing a Sansible revision by hand: bump `__version__` in `src/sansible/__init__.py`
(for example `2.22.0.1` to `2.22.0.2`), merge, then push the tag `v2.22.0.2`. The release
workflow tests and publishes it.

## Background

Sansible started as a small, from-scratch Ansible-compatible runner. That engine is preserved
on the [`legacy-0.4`](https://github.com/small-ansible/sansible/tree/legacy-0.4) branch, and
`pip install sansible==0.4.1` still installs it. Research into running the real ansible-core
on Windows showed that the gap is small and well-defined, so Sansible now ships ansible-core
itself. The research, measurements and findings are in
[experiments/ansible-core-windows](experiments/ansible-core-windows/README.md). The goal is to
upstream these changes to ansible-core, so that eventually this package is no longer needed.

## License

GPL-3.0-or-later, the same as ansible-core. Releases 0.4.x and earlier were MIT.
