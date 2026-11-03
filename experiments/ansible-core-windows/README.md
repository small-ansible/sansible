# Experiment: unmodified ansible-core as a native Windows controller

**Question:** instead of re-implementing Ansible, can we run real `ansible-core` on a
Windows control node by fixing only the parts that are POSIX-specific?

**Answer (November 2026, ansible-core 2.22.0, Python 3.13, Windows Server 2022):** yes,
except for the SSH transport. A compat layer of about 900 lines makes unmodified ansible-core run
`ansible-playbook` and `ansible-galaxy` natively on Windows, with the real
`ansible.windows` collection, over PSRP/WinRM. Workers run in a persistent pool of
**spawned** processes (no fork), and the results are identical to stock fork.

## Worker models (`SANSIBLE_WORKER`)

| Model | How | Process isolation | Where |
|---|---|---|---|
| `fork` | ansible-core's own: one forked process per host per task | ✅ | default where `os.fork` exists (compat does nothing) |
| `pool` | `compat/_spawn_pool.py`: one long-lived *spawned* process per strategy worker slot; each task's inputs are pickled at `start()` | ✅ | default without fork; opt-in elsewhere |
| `thread` | `compat/_threaded_workers.py`: thread per task, with inputs cloned | ❌ | first prototype only; see the thread-safety failure below |

Why spawn works: a forked worker can never write into the controller's memory, so
ansible-core *already* returns everything explicitly: results, display and callbacks over
`FinalQueue`, and inventory changes over the worker→controller RPC added in 2.21/2.22
(`_internal/_rpc_host.py`). Fork is only used to hand **inputs** to the worker cheaply.
The pool pickles those inputs once per task. The ambient controller state fork carried
implicitly is rebuilt explicitly:

- **Once per worker process** (`_ControllerState`): `context.CLIARGS`, display
  verbosity, `init_plugin_loader(collections_path)`, `VaultSecretsContext`, secret-masking
  input files, the RPC server address and authkey (`AutoRegisterRPC.get_client()` "assumes
  the caller was forked"), and session isolation.
- **With every job** (`_JobState`, small): each plugin loader's `_extra_dirs` (role and
  playbook-adjacent plugin dirs added mid-run), `AnsibleCollectionConfig.playbook_paths`,
  and `default_collection`.

Gotcha found along the way: the controller's stdio fds are not inheritable, so a
spawned child starts with fd 2 closed and dies silently during bootstrap. The pool marks
fds 0–2 inheritable before spawning, which mirrors what fork inherits.

### Differential test (`suite/compare.sh`)

`suite.yml` covers:

- vault-encrypted vars
- a role with a custom module in `library/`
- a playbook-adjacent filter plugin
- `group_by` and `add_host` (both go through the RPC path)
- looped `include_tasks`
- block/rescue/always
- `delegate_to` + `run_once`
- `changed_when`
- a deliberately failing host
- a second play targeting groups created at runtime

A callback records every task result.

| Comparison | Result |
|---|---|
| pool vs fork | **identical** (87 records) |
| thread vs fork | identical (87 records) |
| pool under WINSIM vs fork | identical (87 records) |

### ansible-core's own integration tests (`integration/`)

ansible-core v2.22.0's `ansible-test integration --local` was run on 87 worker-relevant
targets. They cover strategies (linear, free, host_pinned, external), handlers and handler
races, blocks, all include/import forms, `add_host`/`group_by`, async, `until`/loops,
`throttle`, `any_errors_fatal`, `ignore_unreachable`, vault/unvault, secret masking,
`no_log`, collections (adjacent, namespaced, relative imports), `module_defaults`, callbacks,
the debugger, `pause`, `vars_prompt`, `task-timeout`, `result_pickle_error` and
`unexpected_executor_exception`. Each target ran twice, once with stock fork and once with
the pool injected into every ansible process via a `.pth` boot hook
(`integration/install_boot.sh`). The boot log confirmed 1,462 ansible processes in pool
mode, 751 spawned workers and 0 fork-mode processes.

| | fork | pool |
|---|---|---|
| Pass | 85 / 87 | **85 / 87** |
| Targets where fork and pool differ | | **0** |
| Failing in both (host environment: no readable syslog/journal; `pip` into an externally-managed interpreter) | `module_no_log`, `template_jinja2_non_native` | same |
| Total wall time | 1,202 s | 1,449 s (+20%) |

The first pass had 6 targets that passed on fork and failed on pool. Each one exposed a
place where ansible-core silently relies on fork. These are useful upstream findings:

| Target(s) | Hidden fork assumption | Fix in `_spawn_pool.py` |
|---|---|---|
| `handlers` (include_role in a loop) | `Role._hash` is a lazily built `MappingProxyType` cache, which can't be pickled | `Role.__getstate__` drops the cache |
| `set_fact` (jsonfile fact cache) | Persistent cache plugins are wrapped in a wrapt `ObjectProxy` (`PluginInterposer`) that refuses to pickle | Reduce to "rebuild the same cache plugin from config" in the worker; data lives in the shared store |
| `collections`, `loop-connection`, `module_defaults` | `AnsibleCollectionConfig.playbook_paths` getter returns `<dir>/collections`, but the setter appends `collections` again (not round-trippable) | Sync the directory names instead |
| `strategy_free` | The free strategy reads the private `worker._task._uuid` | `PoolWorker` exposes `_task` and `_host` |

Earlier findings of the same kind:

- The controller's stdio isn't inheritable, so a spawned child starts with fd 2 closed.
- `AutoRegisterRPC.get_client()` "assumes the caller was forked from the controller".

The +20% wall time comes from short-lived playbooks: every `ansible-playbook` invocation in
the suite (about 1,500 of them) pays the worker spawn cost. Long playbooks amortize it
(see the benchmark below, where the pool beats fork). `forkserver` on POSIX, or spawning
slots in parallel ahead of the first task, would remove most of it.

### Performance

| Benchmark | fork | pool | thread |
|---|---|---|---|
| Linux, 20 hosts × 20 tasks, `-f 10`, local connection | 16.2 s | **14.5 s** | 13.9 s |
| Windows, 5 hosts × 20 controller-side tasks, `-f 5` | n/a | 2.6 s | 1.5 s ⚠️ |
| Windows, 5 hosts × `win_shell` sleep 3s over PSRP, `-f 1` / `-f 5` | n/a | 20.4 / 6.3 s | 19.9 / 4.7 s |

The pool beats fork on Linux: reusing warm processes is cheaper than forking a large
controller 400 times. On Windows the pool pays a one-off worker spawn cost of about 1.5 s
for 5 workers (process creation plus ansible imports).

⚠️ **Thread mode hit a real thread-safety bug on Windows.** Two threads imported the same
filter plugin concurrently, and one saw a half-initialized module (`module
'ansible.plugins.filter.core_…' has no attribute 'FilterModule'`). This is the class of
problem behind upstream abandoning threads
([ansible/ansible#44280](https://github.com/ansible/ansible/pull/44280)). The pool mode
does not share interpreter state, so it ran clean.

## What was verified on real Windows

| Scenario | Result |
|---|---|
| Stock `ansible-playbook` on Windows, no compat | ❌ fails at import (`os.get_blocking` → `WinError 5`) |
| Controller-only play (loops, `set_fact`, `assert`, `template`/`env` lookups, handlers) | ✅ |
| `ansible-galaxy collection install ansible.windows` | ✅ |
| Windows → Windows over PSRP (SSPI, no password): facts, `win_ping`, `win_shell`, `win_file`, `win_copy`, `win_template`, `win_stat`, handler | ✅ `ok=10 failed=0` |
| Second run (idempotence) | ✅ only `win_shell` reports changed (expected) |
| 5 hosts, `win_shell` sleeping 3s | ✅ `-f 1`: 19.8s, `-f 5`: 4.6s (threaded workers run in parallel) |
| Windows → anything over the stock `ssh` plugin | ❌ `os.O_NONBLOCK`; the plugin also needs pty, `select()` on pipes and ControlPersist |

## Blockers found and how the prototype handles them

| # | Blocker in ansible-core | Kind | Fix in `compat/` |
|---|---|---|---|
| 1 | `WorkerProcess` uses `multiprocessing.get_context('fork')`, forking one process per host per task | Architectural | `_spawn_pool.py`: persistent spawned worker pool (see above) |
| 2 | Module-level imports of `fcntl`, `termios`, `tty`, `pty`, `pwd`, `grp`, `resource` | Import | `_posix_stubs.py`: stand-in modules (`msvcrt` locking for `fcntl`) |
| 3 | `utils/display.py` loads libc via ctypes for `wcwidth`/`wcswidth` | Import | Pure-Python `wcwidth` |
| 4 | `ansible.cli` checks `os.get_blocking()` on stdio (raises on Windows) and requires a UTF-8 locale (Windows default is cp1252) | Startup | Tolerant `get_blocking`; `setlocale('')` → `.UTF-8` |
| 5 | `os.register_at_fork`, `os.uname`, `os.getuid`, `signal.SIGUSR1` | API | Guarded call sites / shims |
| 6 | Controller paths assumed to be `/`-separated: dataloader regex, `Origin` tags, collection loader, module FQN regex | Path semantics | Exact-text source patches |
| 7 | `ShellBase` (POSIX targets) validates and joins **remote** paths with the controller's `os.path` | Path semantics (an upstream bug, visible only on a Windows controller) | Use `posixpath` |
| 8 | "World-writable" checks on `st_mode` (always true on Windows) cause `ansible.cfg` and the Galaxy cache to be ignored | Security heuristic | Skip on `nt` |
| 9 | `ssh` connection plugin: OpenSSH with ControlPersist, pty, `select()` on pipes, `O_NONBLOCK` | Transport | **Not solved.** Needs a pure-Python SSH connection plugin (asyncssh or paramiko) |
| 10 | `local` connection runs `/bin/sh`, and Python modules import `fcntl`/`pwd` at the target | Transport | **Not solved.** Matters for `delegate_to: localhost` / `connection: local` with real modules |

Source patches (`compat/_source_patches.py`) are exact-text replacements applied at
import time. If a target line changes in a new ansible-core release, the import fails
loudly instead of silently running unpatched code.

## Not yet tested / known gaps

- Interactive prompts on **Windows**: `pause`, `vars_prompt` and the debugger pass under the pool on Linux, but termios is stubbed on Windows.
- Ctrl-C and `SIGTERM` handling in pool mode (workers ignore SIGINT and the controller shuts the pool down).
- Large inventories: per-task pickled `task_vars` grow with `hostvars`; only measured at about 150 KiB.
- The rest of the integration suite (about 220 more non-root targets, plus root/destructive ones in a container), and running it on macOS and Windows runners.
- Other start methods: `forkserver` would cut Linux worker startup and should work with the same code.
- Path-semantics audit of action plugins (`copy`: 25 `os.path` uses, `fetch`: 8, `module_common`: 18) for Windows controller → Linux target.
- `ansible-vault`, `ansible-inventory`, `ansible-doc`, `ansible-test`.

## Running it

```bash
# Linux, simulating Windows (blocks POSIX modules, removes fork):
WINSIM=1 COMPAT=1 python run.py -i playbooks/inv.ini playbooks/pb.yml
```

```bash
# Linux, spawn pool with real fork still available:
COMPAT=1 SANSIBLE_WORKER=pool python run.py -i playbooks/inv.ini playbooks/pb.yml
```

```bash
# Differential test against stock fork:
PYTHON=/path/to/venv/bin/python suite/compare.sh
```

```bash
# ansible-core integration targets under the pool. Use two dedicated interpreters
# (e.g. `uv python install 3.13 --install-dir ...`) with ansible-core's requirements
# plus pexpect and passlib installed; put the boot hook in the pool one only.
integration/install_boot.sh /path/to/pool-python3.13
```

```bash
integration/run_targets.sh /path/to/base-python3.13 /path/to/ansible-core-v2.22.0 out/fork
```

```bash
integration/run_targets.sh /path/to/pool-python3.13 /path/to/ansible-core-v2.22.0-copy out/pool
```

```bat
:: Windows (venv with ansible-core==2.22.0 and pypsrp):
set COMPAT=1
venv\Scripts\python run.py -i playbooks\inv_psrp.ini playbooks\win_psrp.yml
```

On a host that has `fork`, the compat layer does nothing.

## Licensing note

ansible-core is GPLv3+. Patching it at runtime and distributing that together with it
(for example as a PyInstaller bundle) makes the combined work GPLv3. MIT-licensed shim code can
be combined with it. Get proper advice before shipping.
