# Sansible — AI Context Prompt

> **Purpose**: Copy this document into a new AI session to quickly bring it up to speed on the Sansible project.

---

## Project Summary

**Sansible** is a minimal, pure-Python Ansible runner designed to:
- Run CyberArk PAS deployment playbooks
- Work as a native Windows control node (no WSL)
- Package as a `py3-none-any` wheel (no compiled extensions)

**Philosophy**: 80% of Ansible's value with 20% of the code. Fail fast on unsupported features.

---

## Architecture

```
CLI (san run, sansible-playbook)
  ↓
Engine (runner.py orchestrates everything)
  ↓
├── playbook.py   — YAML parsing, FQCN normalization
├── templating.py — Jinja2 with StrictUndefined
├── scheduler.py  — asyncio parallel execution
  ↓
Connections
├── local.py      — subprocess for localhost
├── ssh_asyncssh.py — SSH via asyncssh library
├── winrm_psrp.py  — WinRM via pypsrp library
  ↓
Modules (builtin_*.py, win_*.py)
```

**Linear Strategy**: For each task → run on all hosts concurrently (up to `--forks`) → next task.

---

## Key Files

| Path | Purpose |
|------|---------|
| `src/sansible/san_cli.py` | Main entry point |
| `src/sansible/engine/runner.py` | **Orchestrator** - ties everything together |
| `src/sansible/engine/playbook.py` | YAML parsing, task/block handling |
| `src/sansible/engine/scheduler.py` | Async parallel execution |
| `src/sansible/connections/base.py` | Connection ABC |
| `src/sansible/modules/base.py` | Module ABC + registry |

---

## Supported Features

### Modules
**Linux**: `command`, `shell`, `raw`, `copy`, `file`, `template`, `debug`, `set_fact`, `fail`, `assert`, `setup`, `stat`, `lineinfile`, `wait_for`

**Windows**: `win_command`, `win_shell`, `win_copy`, `win_file`, `win_service`, `win_stat`, `win_lineinfile`, `win_wait_for`

### Task Features
- `when` conditionals
- `loop` / `with_items`
- `register` variables
- `changed_when` / `failed_when`
- `ignore_errors`
- `check_mode` / `diff`
- `notify` handlers
- `block/rescue/always`
- `become` privilege escalation

### Play Features
- `gather_facts` / `setup`
- `handlers` with `listen`
- `pre_tasks` / `tasks` / `post_tasks`
- `vars` / `vars_files`
- `roles` with defaults/tasks

---

## Out of Scope (Raise UnsupportedFeatureError)

- `delegate_to`, `async/poll`
- Galaxy collections
- Dynamic inventory
- Vault encryption
- Lookups (except basic ones)
- `include_tasks`, `import_role`

---

## Commands

```bash
# Install
pip install -e ".[all,dev]"

# Run playbook
san run -i inventory.ini playbook.yml

# With options
san run -i inventory.ini playbook.yml --check --diff -v --forks 10

# Run tests
pytest tests/unit/ -v
pytest tests/e2e/playbooks/00_connectivity.yml  # E2E with real hosts
./tests/e2e/run_all_tests.sh  # All E2E tests

# Build wheel
python -m build
```

---

## Test Infrastructure

E2E tests are in `tests/e2e/`:
```
tests/e2e/
├── test_inventory.ini.template  # Copy and fill in host details
├── run_all_tests.sh             # Single command to run all tests
├── playbooks/
│   ├── 00_connectivity.yml      # Verify hosts reachable
│   ├── 01_basic_modules.yml     # Core modules
│   ├── 02_file_operations.yml   # file/copy/stat
│   ├── 03_conditionals.yml      # when/loop
│   ├── 04_handlers.yml          # notify/listen
│   ├── 05_blocks.yml            # block/rescue/always
│   ├── 06_become.yml            # Privilege escalation
│   ├── 07_facts.yml             # gather_facts/setup
│   ├── 08_parallel.yml          # --forks testing
│   ├── 09_check_diff.yml        # --check/--diff
│   └── 10_full_scenario.yml     # Complete deployment
└── golden/
    └── compare_with_ansible.sh  # Compare Sansible vs ansible-playbook
```

---

## Adding New Features

### New Module
1. Create `src/sansible/modules/builtin_<name>.py`
2. Inherit from `Module`, add `@register_module`
3. Define `name`, `required_args`, `optional_args`
4. Implement `async def run() -> ModuleResult`
5. Import in `modules/base.py` → `_import_builtin_modules()`

### New Connection
1. Implement `Connection` ABC from `connections/base.py`
2. Methods: `connect()`, `close()`, `run()`, `put()`, `get()`, `mkdir()`, `stat()`
3. Register in `engine/runner.py` → `_get_connection_class()`

---

## Error Handling

| Exception | Exit Code | When |
|-----------|-----------|------|
| `ParseError` | 3 | Invalid YAML |
| `UnsupportedFeatureError` | 4 | Outside supported subset |
| `ConnectionError` | 2 | Host unreachable |
| `ModuleError` | 2 | Module execution failure |

---

## Current Status (v0.2.0)

✅ All core features implemented
✅ 209 unit tests passing
✅ Example playbooks for all features
✅ E2E test infrastructure ready
✅ Wheel builds successfully

**Reference**: CyberArk playbooks at `/home/adam/projects/old/cyberark-pas-deployment-ansible/`

---

## Quick Context Questions

When starting work, an AI assistant should ask:
1. What specific feature or fix are you working on?
2. Should changes be for Linux, Windows, or both?
3. Are there related tests that need updating?
4. Should I compare behavior with real Ansible?

---

## Code Style

- All modules are `async def run()`
- Jinja2 uses `StrictUndefined` (fail on undefined vars)
- Use exceptions from `engine/errors.py` with proper exit codes
- Mock connections in tests (see `tests/unit/test_executor_linear.py`)
- Pure Python only — no compiled extensions
