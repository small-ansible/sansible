# AI Agent Instructions — Sansible (Minimal Ansible-Compatible Runner)

> **Last Updated:** 2025-01-11
> **Status:** M5 Complete — CyberArk PAS Ready

## Mission Statement

**Sansible** is a minimal, pure-Python, Windows-native Ansible-compatible playbook runner. It enables DevOps engineers on Windows to run simple Ansible playbooks against Windows (WinRM/PSRP) and Linux (SSH) targets without installing full Ansible (which requires WSL on Windows).

### Core Use Case
> "I'm on Windows and want to run simple playbooks—either through WinRM to Windows targets or SSH to Linux targets. The playbooks should be compatible with Ansible, but I don't need full parallelism or every feature. I need the smallest possible Python footprint that can interpret and execute Ansible playbooks."

## Project Principles

1. **Minimal Footprint** — Only essential dependencies (PyYAML, Jinja2 core; asyncssh/pypsrp optional)
2. **Pure Python Wheel** — Must build as `py3-none-any` for true cross-platform install
3. **Windows Native** — Run directly on Windows, no WSL required
4. **Documented Subset** — Explicitly define what's supported; fail fast on unsupported features
5. **Ansible Compatibility** — Existing playbooks should work with minimal changes
6. **Proof Over Claims** — Golden tests compare Sansible vs `ansible-playbook` for correctness

---

## What This Is (and Isn't)

### ✅ What Sansible IS
- A **playbook runner** for simple automation tasks
- An **Ansible-compatible subset** implementation
- A **Windows-native control node** (no WSL needed)
- A **proof-of-concept** for minimal Ansible execution

### ❌ What Sansible IS NOT
- A **full Ansible replacement** (use `ansible-core` for complex workflows)
- A **collection/role manager** (no Galaxy support)
- A **complete module library** (only core modules)
- A **drop-in binary replacement** (some playbooks need adaptation)

---

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| CLI (`sansible`, `sansible-playbook`) | ✅ Complete | Works end-to-end |
| INI Inventory Parser | ✅ Complete | Groups, children, vars |
| YAML Inventory Parser | ✅ Complete | Standard format |
| Playbook Parser | ✅ Complete | FQCN, blocks, handlers |
| Jinja2 Templating | ✅ Complete | Filters, tests, conditionals |
| Local Connection | ✅ Complete | Localhost execution |
| SSH Connection | ✅ Complete | Docker integration tests pass |
| WinRM/PSRP Connection | ✅ Complete | All modules implemented |
| Async Scheduler | ✅ Complete | `--forks` parallelism |
| Core Modules | ✅ Complete | command, shell, raw, copy, file, template, stat, lineinfile, wait_for, setup |
| Windows Modules | ✅ Complete | win_shell, win_command, win_copy, win_file, win_service, win_stat, win_lineinfile, win_wait_for |
| JSON Output Mode | ✅ Complete | `--json` flag |
| Check Mode | ✅ Complete | `--check` flag |
| Diff Mode | ✅ Complete | `--diff` flag |
| Handlers | ✅ Complete | notify/listen support |
| Block/Rescue/Always | ✅ Complete | Error handling blocks |
| Become | ✅ Complete | Privilege escalation |
| Roles | ✅ Complete | Simple role support |
| Golden Tests | ✅ Complete | Sansible vs ansible-playbook comparison |

---

## Role
You are a senior Python engineer building a minimal "Ansible-like" runner called **Sansible**.
You will implement a **small-footprint** executable that can run **basic Ansible playbooks** against:
- Linux hosts over **SSH** (`asyncssh`)
- Windows hosts over **WinRM/PSRP** (`pypsrp`)

The project must include:
- A working CLI (`san`)
- Core engine for playbooks + inventory + parallel execution
- Minimal module set (copy + remote command execution)
- Integration tests that compare Sansible behavior to real `ansible-playbook` (golden tests)
- Clear docs + "AI handoff" docs for future agents

IMPORTANT: Do not aim for full Ansible compatibility. Implement a **documented supported subset** that matches common/simple playbooks. If a playbook uses unsupported features, fail fast with a precise error.

## North Star
Goal: "Tiny Ansible footprint" that can run simple playbooks with minimal changes:
- Inventory-driven host selection
- Parallel execution across hosts (forks-like)
- Copy file(s) to target
- Execute commands/scripts remotely
- Windows via PowerShell (WinRM/PSRP)
- Linux via SSH
- Deterministic output and sensible exit codes

## Hard Constraints
- Keep runtime dependencies minimal.
- Separate dependencies by extras:
  - `sansible[ssh]` for SSH deps (`asyncssh`)
  - `sansible[winrm]` for WinRM deps (`pypsrp`)
  - `sansible[all]` for all connection types
  - `sansible[dev]` for tests, linting, ansible oracle, docker tooling
- **Pure Python Wheel**: The final wheel MUST be `py3-none-any`
- **No compiled extensions**: Zero .so/.pyd/.dylib in runtime dependencies
- Tests must be runnable locally and in CI
- Provide excellent error messages and logs
- Provide docs and AI handoff markdown files

---

## Supported Subset v0.1 (Compatibility Contract)

### Inventory

| Feature | Status | Implementation |
|---------|--------|----------------|
| INI format | ✅ | `engine/inventory.py` |
| YAML format | ✅ | `engine/inventory.py` |
| `[group]` sections | ✅ | Group membership |
| `[group:children]` | ✅ | Group inheritance |
| `[group:vars]` | ✅ | Group variables |
| Host patterns (ranges) | ✅ | `web[01:10].example.com` |
| Inline host vars | ✅ | `host ansible_host=x ansible_user=y` |
| `host_vars/` directory | ✅ | Per-host variable files |
| `group_vars/` directory | ✅ | Per-group variable files |
| `--limit` pattern | ✅ | Basic patterns |
| Dynamic inventory | ❌ | Static only |

### Playbooks

| Feature | Status | Notes |
|---------|--------|-------|
| Multiple plays | ✅ | Sequential execution |
| `hosts` | ✅ | Required per play |
| `vars` | ✅ | Play-level variables |
| `vars_files` | ✅ | YAML files only |
| `tasks` | ✅ | Task list |
| `gather_facts: false` | ✅ | Default is false |
| `gather_facts: true` | ✅ | setup module gathers facts |
| `handlers` | ✅ | Handler sections with notify/listen |
| `roles` | ✅ | Simple role support |

### Tasks

| Feature | Status | Notes |
|---------|--------|-------|
| `name` | ✅ | Task description |
| Module invocation | ✅ | By key or FQCN |
| `args` / inline args | ✅ | Dict or `key=value` |
| `register` | ✅ | Capture output |
| `when` | ✅ | Boolean/Jinja expressions |
| `loop` / `with_items` | ✅ | List iteration |
| `loop_control` | ⚠️ | `loop_var` only |
| `ignore_errors` | ✅ | Continue on failure |
| `changed_when` | ✅ | Override changed |
| `failed_when` | ✅ | Override failed |
| `notify` | ✅ | Trigger handlers |
| `become` | ✅ | Privilege escalation |
| `block/rescue/always` | ✅ | Error handling blocks |

### Modules

| Module | Status | Connection |
|--------|--------|------------|
| `command` | ✅ | local/ssh |
| `shell` | ✅ | local/ssh |
| `raw` | ✅ | local/ssh |
| `copy` | ✅ | local/ssh |
| `file` | ✅ | local/ssh |
| `template` | ✅ | local/ssh |
| `stat` | ✅ | local/ssh |
| `lineinfile` | ✅ | local/ssh |
| `wait_for` | ✅ | local/ssh |
| `setup` | ✅ | all |
| `debug` | ✅ | all |
| `set_fact` | ✅ | all |
| `fail` | ✅ | all |
| `assert` | ✅ | all |
| `win_command` | ✅ | winrm |
| `win_shell` | ✅ | winrm |
| `win_copy` | ✅ | winrm |
| `win_file` | ✅ | winrm |
| `win_service` | ✅ | winrm |
| `win_stat` | ✅ | winrm |
| `win_lineinfile` | ✅ | winrm |
| `win_wait_for` | ✅ | winrm |

### Templating

| Feature | Status | Notes |
|---------|--------|-------|
| `{{ variable }}` | ✅ | Interpolation |
| `default` filter | ✅ | Default values |
| `lower` / `upper` | ✅ | Case conversion |
| `replace` | ✅ | String replacement |
| `to_json` / `to_yaml` | ✅ | Serialization |
| `regex_replace` | ✅ | Regex substitution |
| `is defined` test | ✅ | Variable existence |
| Custom filters | ❌ | Built-in only |
| `lookup()` | ❌ | No lookups |

### Connections

| Type | Status | Dependency |
|------|--------|------------|
| `local` | ✅ | None |
| `ssh` | ✅ | `asyncssh` |
| `winrm` / `psrp` | ✅ | `pypsrp` |

---

## Non-Goals (Fail Fast)

These features are **explicitly not supported** and will raise `UnsupportedFeatureError`:

- Ansible collections/Galaxy dependency resolution
- `async`/`poll` tasks
- Complex variable precedence identical to Ansible
- Jinja2 sandbox parity
- Network devices, vault, callbacks/plugins
- `include_tasks`, `import_tasks`, `include_role`, `import_role`
- `delegate_to`

---

## Repo Layout

```
sansible/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/sansible/
│   ├── __init__.py
│   ├── cli.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── inventory.py
│   │   ├── playbook.py
│   │   ├── templating.py
│   │   ├── scheduler.py
│   │   ├── results.py
│   │   └── errors.py
│   ├── connections/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── ssh_asyncssh.py
│   │   ├── winrm_psrp.py
│   │   └── transfer.py
│   └── modules/
│       ├── __init__.py
│       ├── base.py
│       ├── builtin_copy.py
│       ├── builtin_command.py
│       ├── builtin_shell.py
│       ├── builtin_raw.py
│       ├── win_copy.py
│       ├── win_shell.py
│       └── win_command.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│       ├── inventory.ini
│       └── playbooks/
│           ├── linux_smoke.yml
│           ├── windows_smoke.yml
│           └── mixed_smoke.yml
├── docs/
│   ├── ARCHITECTURE.md
│   ├── COMPATIBILITY.md
│   ├── TESTING.md
│   ├── ROADMAP.md
│   ├── AI_HANDOFF.md
│   └── AI_TASKS_NEXT.md
└── .github/workflows/ci.yml
```

---

## CLI Spec

Command:
```
san run -i INVENTORY playbook.yml [--limit ...] [--forks N] [--json] [--check] [--diff]
```

Only implement `--check/--diff` as "recognized but not supported" (error) in v0.1.

Exit codes:
- 0: success for all hosts
- 2: one or more hosts failed
- 3: invalid input / parse errors
- 4: unsupported feature encountered

---

## Implementation Details

### Inventory Parser
- Parse INI inventory format:
  - `[group]`
  - `[group:children]`
  - `[group:vars]`
  - host lines: `host ansible_host=... ansible_user=... ansible_port=... ansible_connection=ssh|winrm`
- Store host vars and group vars.
- Merge with `group_vars/` and `host_vars/` YAML (optional but implement).

### Playbook Parser
- Use `yaml.safe_load_all`.
- Normalize module invocation:
  - `copy:` and `ansible.builtin.copy:` map to module id `copy`
- Parse task args:
  - Inline style: `copy: src=a dest=b`
  - Dict style: `copy: {src: a, dest: b}`
- Validate required args per module; error nicely.

### Templating
- Jinja2 Environment with strict undefined.
- Render strings recursively in dict/list structures.
- Minimal filters:
  - `default`, `lower`, `upper`, `replace`, `to_json`
- Evaluate `when`:
  - render as Jinja expression returning truthy
  - allow simple forms: `var == "x"`, `var is defined`

### Scheduler / Parallelism
- Use `asyncio`.
- For each task:
  - create per-host coroutine
  - run with semaphore sized `forks`
  - gather results
- Maintain per-host context:
  - vars
  - registered vars
  - connection object
  - failed flag

### Connection Abstractions
Define base class:
- `run(command: str, shell: bool, timeout: int|None) -> RunResult`
- `put(local_path, remote_path) -> None`
- `mkdir(remote_path) -> None` (best-effort)

SSH:
- run via remote shell or exec
- put via SFTP

Windows (pypsrp):
- run via PowerShell
- put via chunked base64:
  - read file bytes
  - split chunks (e.g., 700KB)
  - for each chunk: send PS that appends bytes to temp file
  - finalize move to dest

### Modules
Implement module interface:
- input: args dict + host context
- output: `{changed: bool, rc: int, stdout: str, stderr: str, ...}`

Modules to implement:
- `copy`: args `src`, `dest`
- `command`: run without shell interpretation
- `shell`: run via shell (`/bin/sh -lc` on linux; PowerShell on windows)
- `raw`: run exactly as provided
- Windows: `win_shell`, `win_command`, `win_copy`

### Output
- Print task banner `TASK [name]`
- For each host: `ok: [host]`, `changed: [host]`, `failed: [host] (rc=...)`
- Final recap: `ok= changed= failed= skipped=` per host
- `--json`: machine-readable results

---

## Testing Strategy

### Unit tests
- inventory parsing
- playbook parsing and normalization
- templating + when evaluation
- scheduler semantics (forks limit)

### Integration tests (Linux)
Use Docker to run an SSH target container and run playbooks against it.
- Test playbook `linux_smoke.yml`: copy a file, run cat, run shell
- Assert Sansible returns success, compare Sansible with `ansible-playbook` oracle

### Integration tests (Windows)
- CI on GitHub Actions windows runner with WinRM listener
- Local dev: `pytest -m windows`, skip if env vars not set

### Golden tests vs Ansible
- Run `ansible-playbook` and `san run` with same inputs
- Compare: both exit success, side effects match

---

## Packaging
- `pyproject.toml` with extras:
  - `ssh = ["asyncssh>=2.14.0"]`
  - `winrm = ["pypsrp>=0.8.0"]`
  - `dev = ["pytest", "pytest-asyncio", "ruff", "mypy", "ansible-core", "docker", ...]`
- Console entry points: 
  - `san=sansible.san_cli:main`
  - `sansible-playbook=sansible.cli.playbook:main`

---

## Documentation (must write)
- `README.md`: what it is, quick start
- `docs/ARCHITECTURE.md`: data flow, scheduler, connections, modules
- `docs/COMPATIBILITY.md`: supported subset + unsupported features
- `docs/TESTING.md`: how to run tests
- `docs/ROADMAP.md`: staged expansion
- `docs/AI_HANDOFF.md`: how to continue work
- `docs/AI_TASKS_NEXT.md`: backlog for future agents

---

## Current Status (Updated 2025-01-11)

### COMPLETED ✅
- [x] Working `san run` CLI
- [x] Working `sansible-playbook` CLI
- [x] INI + YAML inventory support + vars merge
- [x] Playbook parser + subset semantics
- [x] Jinja2 templating + basic `when` + loops
- [x] Async scheduler with forks limit
- [x] Local connection (localhost execution)
- [x] Modules: command, shell, raw, copy, debug, set_fact, fail, assert
- [x] Windows modules: win_shell, win_command, win_copy (code complete)
- [x] SSH connection (asyncssh) - code complete
- [x] WinRM/PSRP connection - code complete
- [x] Console output with ANSI colors
- [x] Unit tests (41 passing)
- [x] Pure Python wheel (py3-none-any verified)

### VERIFIED WORKING
```bash
san run -i tests/fixtures/inventory.ini tests/fixtures/playbooks/linux_smoke.yml
# Runs successfully with copy, shell, command, debug, set_fact, assert modules
```

### REMAINING
- [ ] Integration tests with Docker SSH target
- [ ] Integration tests on real Windows host
- [ ] Golden tests against `ansible-playbook`
- [ ] JSON output mode
- [ ] --check mode implementation

---

## Finish Condition
Work until:
- `pytest` passes (unit + linux integration)
- Golden tests comparing Sansible vs Ansible pass for supported playbooks
- Docs are accurate and explicit
- `san` can run at least `linux_smoke.yml` end-to-end ✅ DONE

Now implement everything. No stubs. No "TODO" left in core paths. If something is out of scope, error clearly and document it.
