# Sansible — Copilot Instructions

## Project Philosophy

Sansible is a **minimal, pure-Python Ansible runner** — NOT a full port. Delivers 80% of Ansible's value with 20% of the code.

**Hard constraints:**
- **Pure Python wheel** (`py3-none-any`) — zero compiled extensions (no .so/.pyd)
- **Windows-native control node** — no WSL required
- **Fail fast** on unsupported features with `UnsupportedFeatureError`

**Goal:** Run CyberArk PAS deployment playbooks (WinRM + SSH) from Windows.

## Architecture

```
CLI → Engine → Connections → Modules
     runner.py orchestrates all
```

| Layer | Key Files | Purpose |
|-------|-----------|---------|
| CLI | `neo_cli.py`, `cli/*.py` | Entry points (`san run`, `sansible-playbook`) |
| Engine | `engine/runner.py` | **Main orchestrator** — ties everything together |
| Engine | `engine/playbook.py` | YAML parsing, FQCN normalization (`ansible.builtin.copy` → `copy`) |
| Engine | `engine/templating.py` | Jinja2 with `StrictUndefined` (fail on undefined vars) |
| Engine | `engine/scheduler.py` | asyncio parallel execution (linear strategy, respects `--forks`) |
| Connections | `connections/local.py` | subprocess for localhost |
| Connections | `connections/ssh_asyncssh.py` | asyncssh (requires `[ssh]` extra) |
| Connections | `connections/winrm_psrp.py` | pypsrp (requires `[winrm]` extra) |
| Modules | `modules/builtin_*.py`, `win_*.py` | `@register_module` decorated classes |

**Linear strategy:** For each task → run on all hosts concurrently (up to `--forks`) → next task.

## Developer Workflow

```bash
pip install -e ".[dev]"           # Setup with dev deps (includes ansible-core for oracle)
pytest tests/unit/ -v             # Fast unit tests (no network)
pytest tests/golden/ -v           # Compare Sansible vs ansible-playbook (oracle)
pytest tests/integration/ -v      # Docker SSH tests
san run -i tests/fixtures/inventory.ini tests/fixtures/playbooks/linux_smoke.yml
```

## Adding a New Module

Create `src/sansible/modules/builtin_<name>.py`:

```python
from sansible.modules.base import Module, ModuleResult, register_module

@register_module
class MyModule(Module):
    name = "my_module"
    required_args = ["dest"]
    optional_args = {"force": True}

    async def run(self) -> ModuleResult:
        # Use: self.connection.run(), self.connection.put(), self.connection.stat()
        return ModuleResult(changed=True, msg="done")
```

Then import in `modules/base.py` → `_import_builtin_modules()`.

## Adding a New Connection

Implement `Connection` ABC from `connections/base.py`:
- `async def connect()`, `close()`, `run()`, `put()`, `get()`, `mkdir()`, `stat()`

Register in `engine/runner.py` → `_get_connection_class()`.

## Error Handling

Use exceptions from `engine/errors.py` — they define exit codes:

| Exception | Exit | When |
|-----------|------|------|
| `ParseError` | 3 | Invalid inventory/playbook YAML |
| `UnsupportedFeatureError` | 4 | Feature outside supported subset |
| `ConnectionError` | 2 | Host unreachable |
| `ModuleError` | 2 | Module execution failure |

## Key Conventions

1. **All modules are async** — `async def run()` using `await`
2. **Jinja2 StrictUndefined** — undefined variables raise immediately
3. **Exit codes**: 0=success, 2=host failure, 3=parse error, 4=unsupported
4. **Extras**: `[ssh]` asyncssh, `[winrm]` pypsrp, `[dev]` testing + ansible-core
5. **Mock connections in tests** — see `MockConnection` in `tests/unit/test_executor_linear.py`

## Out of Scope (Raise UnsupportedFeatureError)

- `async/poll`
- Galaxy collections, lookups

## Supported Features

**Task Includes:**
- `include_tasks` / `import_tasks` — load external task files
- `include_role` / `import_role` — dynamic role inclusion
- `delegate_to` — execute task on different host

**Dynamic Inventory:**
- Executable scripts returning JSON
- Standard Ansible JSON format with `_meta` hostvars

**Vault:**
- `--vault-password-file` — path to vault password file
- `--ask-vault-pass` — prompt for vault password
- Requires `cryptography` package for decryption

**Privilege Escalation:**
- `become: true/false` — enable/disable privilege escalation
- `become_user` — target user (default: root)
- `become_method` — method (sudo, su)

**Error Handling:**
- `block/rescue/always` — block structure with error handling
- `ignore_errors` — continue on failure

**Handlers:**
- `handlers` — define handler tasks in play
- `notify` — trigger handlers on task change
- `listen` — handler can listen to multiple triggers

**Galaxy Module Support:**
- FQCNs like `ansible.builtin.copy` — automatically maps to native modules
- `ansible.windows.*` — maps to native `win_*` modules
- `ansible.posix.*`, `community.general.*` — executed via remote Ansible on Linux targets
- Windows Galaxy modules — falls back to native or returns clear error
- See [docs/GALAXY.md](docs/GALAXY.md) for full details

## Supported Modules

**Linux (builtin_*.py):**
- `command`, `shell`, `raw` — execute commands
- `copy`, `file`, `template` — file management
- `debug`, `set_fact`, `fail`, `assert` — flow control
- `setup` — gather_facts (hostname, OS family, distribution)
- `stat` — file status
- `lineinfile` — line management in files
- `wait_for` — wait for port/file conditions

**Windows (win_*.py):**
- `win_command`, `win_shell` — execute commands
- `win_copy`, `win_file` — file management
- `win_service` — service management (start/stop/restart/set_mode)
- `win_stat` — file status
- `win_lineinfile` — line management
- `win_wait_for` — wait for port/file conditions

## Testing Patterns

| Type | Location | Notes |
|------|----------|-------|
| Unit | `tests/unit/` | Mock connections, no network |
| Golden | `tests/golden/` | JSON output comparison vs `ansible-playbook` |
| Integration | `tests/integration/` | Docker SSH containers |

Golden tests run same playbook with Sansible and real Ansible, compare JSON results.

**JSON output format** (`--json` flag):
```json
{"plays": [{"name": "...", "tasks": [{"host": "...", "status": "ok|changed|failed", "changed": bool}]}]}
```

## Examples & Fixtures

- `examples/inventory.ini` — sample INI inventory with groups
- `examples/linux_playbook.yml` — basic Linux tasks
- `examples/windows_playbook.yml` — WinRM tasks
- `examples/role_demo_playbook.yml` — role usage example
- `tests/fixtures/` — test inventories and playbooks

## Roadmap: CyberArk PAS Compatibility

✅ **All core features complete:**
- `win_service` module — Windows service management (start/stop/restart/set_mode)
- `gather_facts`/`setup` module — minimal facts (hostname, OS family, distribution)
- `--check` mode — dry-run without making changes
- `--diff` mode — show file content differences
- `stat`/`win_stat` — file status checks
- `lineinfile`/`win_lineinfile` — line management in config files
- `wait_for`/`win_wait_for` — wait for port/file availability
- `become` support for privilege escalation (sudo, su)
- `block/rescue/always` for error handling
- `handlers` and `notify` for triggered actions

Reference: CyberArk playbooks at `/home/adam/projects/old/cyberark-pas-deployment-ansible/`

## Documentation

- [docs/AI_HANDOFF.md](docs/AI_HANDOFF.md) — architecture diagrams, key files
- [docs/AI_INSTRUCTIONS.md](docs/AI_INSTRUCTIONS.md) — detailed feature matrix
- [docs/agent/STATUS.md](docs/agent/STATUS.md) — current implementation status
- `upstream/ansible/` — reference implementation (don't copy, use for API understanding)
