# AI Handoff Document — Sansible

> **Purpose:** Enable any AI agent or developer to continue work on Sansible
> **Last Updated:** 2025-01-11
> **Project Status:** v0.2.0 — All core features complete, 209 unit tests passing

---

## Quick Start for New Agents

```bash
# 1. Navigate to project
cd /home/adam/projects/sansible

# 2. Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Verify tests pass (should show 209 passed)
pytest tests/unit/ -q

# 4. Test playbook execution
san run -i tests/fixtures/inventory.ini tests/fixtures/playbooks/linux_smoke.yml

# 5. Read project context docs
cat docs/AI_PROMPT.md           # Quick context for AI agents
cat docs/agent/STATUS.md        # Implementation status
```

---

## Project Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLI Layer                                   │
│  cli/main.py  │  cli/main.py  │  cli/playbook.py  │  cli/inventory.py│
└──────────────┬──────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Engine Layer                                   │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌─────────────────────┐ │
│  │ runner.py │  │playbook.py│ │inventory.py│ │   templating.py    │ │
│  │PlaybookRun│  │  Parser   │  │ Manager   │  │  Jinja2 Engine    │ │
│  └──────────┘  └──────────┘  └───────────┘  └─────────────────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐                          │
│  │scheduler │  │ results  │  │  errors   │                          │
│  │  Async   │  │TaskResult│  │ SansibleError  │                          │
│  └──────────┘  └──────────┘  └───────────┘                          │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Connection Layer                                 │
│  ┌──────────┐  ┌─────────────┐  ┌─────────────┐                     │
│  │ local.py │  │ssh_asyncssh │  │ winrm_psrp  │                     │
│  │LocalConn │  │  SSHConn    │  │  WinRMConn  │                     │
│  └──────────┘  └─────────────┘  └─────────────┘                     │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Module Layer                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ command  │  │  shell   │  │   copy   │  │  debug   │            │
│  ├──────────┤  ├──────────┤  ├──────────┤  ├──────────┤            │
│  │   raw    │  │ set_fact │  │   fail   │  │  assert  │            │
│  ├──────────┤  ├──────────┤  ├──────────┤                          │
│  │win_shell │  │win_command│ │ win_copy │                          │
│  └──────────┘  └──────────┘  └──────────┘                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Files and Their Purpose

### Entry Points (CLI)
| File | Purpose |
|------|---------|
| `src/sansible/cli/main.py` | Main `san` command entry point |
| `src/sansible/cli/main.py` | `sansible` command |
| `src/sansible/cli/playbook.py` | `sansible-playbook` command |
| `src/sansible/cli/inventory.py` | `sansible-inventory` command |

### Engine (Core Logic)
| File | Purpose |
|------|---------|
| `src/sansible/engine/runner.py` | **Main orchestrator** — ties everything together |
| `src/sansible/engine/inventory.py` | INI/YAML inventory parsing |
| `src/sansible/engine/playbook.py` | Playbook YAML parsing |
| `src/sansible/engine/templating.py` | Jinja2 rendering + filters |
| `src/sansible/engine/scheduler.py` | Async task scheduler with forks |
| `src/sansible/engine/results.py` | Result dataclasses |
| `src/sansible/engine/errors.py` | Custom exceptions |

### Connections
| File | Purpose |
|------|---------|
| `src/sansible/connections/base.py` | Abstract Connection base class |
| `src/sansible/connections/local.py` | Localhost execution |
| `src/sansible/connections/ssh_asyncssh.py` | SSH via asyncssh |
| `src/sansible/connections/winrm_psrp.py` | WinRM via pypsrp |

### Modules
| File | Purpose |
|------|---------|
| `src/sansible/modules/base.py` | Module base class + registry |
| `src/sansible/modules/builtin_*.py` | Standard modules (command, shell, etc.) |
| `src/sansible/modules/win_*.py` | Windows-specific modules |

### Platform Utilities
| File | Purpose |
|------|---------|
| `src/sansible/platform/fs.py` | Cross-platform file operations |
| `src/sansible/platform/proc.py` | Cross-platform process execution |
| `src/sansible/platform/paths.py` | Path normalization utilities |

---

## How to Add a New Module

1. **Create the module file:**
```python
# src/sansible/modules/builtin_ping.py
from sansible.modules.base import Module, ModuleResult, module

@module("ping", aliases=["ansible.builtin.ping"])
class PingModule(Module):
    """Simple ping module that returns pong."""
    
    async def execute(self, args: dict, context: dict) -> ModuleResult:
        data = args.get("data", "pong")
        return ModuleResult(
            changed=False,
            data={"ping": data},
            msg=f"ping: {data}",
        )
```

2. **Import in __init__.py:**
```python
# src/sansible/modules/__init__.py
from sansible.modules.builtin_ping import PingModule
```

3. **Write tests:**
```python
# tests/unit/test_modules.py
def test_ping_module():
    # Test the module...
```

---

## How to Add a New Connection Type

1. **Create connection file:**
```python
# src/sansible/connections/my_connection.py
from sansible.connections.base import Connection, RunResult

class MyConnection(Connection):
    async def connect(self) -> None:
        # Establish connection
        pass
    
    async def run(self, command: str, ...) -> RunResult:
        # Execute command
        pass
    
    async def put(self, local_path: str, remote_path: str) -> None:
        # Upload file
        pass
    
    async def close(self) -> None:
        # Clean up
        pass
```

2. **Register in runner.py:**
```python
# src/sansible/engine/runner.py
def _get_connection_class(self, connection_type: str):
    if connection_type == "my_type":
        from sansible.connections.my_connection import MyConnection
        return MyConnection
```

---

## Invariants (Must Always Be True)

1. **Pure Python Wheel** — Never add compiled dependencies to core requirements
2. **Fail Fast** — Unsupported features raise `UnsupportedFeatureError` immediately
3. **Async Execution** — All module execution is async, scheduled via `asyncio`
4. **Connection Lifecycle** — Runner manages connect/close for all connections
5. **Template Safety** — Jinja2 uses `StrictUndefined` to catch variable errors
6. **Exit Codes** — 0=success, 2=host failure, 3=parse error, 4=unsupported feature

---

## Common Issues and Solutions

### "Module not found" error
**Cause:** Module not registered in `ModuleRegistry`
**Fix:** Ensure module has `@module()` decorator and is imported in `__init__.py`

### "asyncssh not found" when testing SSH
**Cause:** SSH extras not installed
**Fix:** `pip install -e ".[ssh]"` or `pip install asyncssh`

### Tests fail with "cannot connect"
**Cause:** Integration tests require Docker or real hosts
**Fix:** Run unit tests only: `pytest tests/unit/`

### Windows paths issues
**Cause:** Path normalization
**Fix:** Use `platform/paths.py` utilities, never raw string concatenation

---

## Where to Look for Specific Changes

| Want to change... | Look in... |
|-------------------|------------|
| CLI arguments | `cli/*.py` |
| Playbook parsing | `engine/playbook.py` |
| Variable resolution | `engine/templating.py` |
| Task execution | `engine/runner.py` |
| Parallel execution | `engine/scheduler.py` |
| SSH behavior | `connections/ssh_asyncssh.py` |
| WinRM behavior | `connections/winrm_psrp.py` |
| Module behavior | `modules/builtin_*.py` |
| Output formatting | `engine/runner.py` (`_print_*` methods) |

---

## Testing Commands

```bash
# All unit tests
pytest tests/unit/ -v

# Specific test file
pytest tests/unit/test_cli.py -v

# With coverage
pytest tests/unit/ --cov=sansible --cov-report=term-missing

# Run a playbook manually
san run -i tests/fixtures/inventory.ini tests/fixtures/playbooks/linux_smoke.yml

# Check pure Python compliance
python -m tools.dep_audit

# Build wheel
pip wheel . -w dist/
```

---

## Next Steps (Priority Order)

1. **SSH Integration Test** — Set up Docker container, test SSH connection
2. **WinRM Integration Test** — Test on real Windows or GitHub Actions
3. **Golden Tests** — Compare Sansible output vs `ansible-playbook`
4. **JSON Output** — Implement `--json` flag
5. **More Modules** — Add `file`, `template`, `lineinfile`

See `docs/AI_TASKS_NEXT.md` for detailed task breakdown.
