# Sansible — Copilot Instructions

## Philosophy & Constraints

Sansible is a **minimal, pure-Python Ansible runner** — delivers 80% of Ansible's value with 20% of the code.

**Hard constraints (non-negotiable):**
- **Pure Python wheel** (`py3-none-any`) — zero compiled extensions
- **Windows-native control node** — no WSL required
- **Fail fast** on unsupported features with `UnsupportedFeatureError`

## Architecture Overview

```
CLI → Engine (runner.py) → Connections → Modules
```

| Layer | Key Files | Purpose |
|-------|-----------|---------|
| Engine | [engine/runner.py](src/sansible/engine/runner.py) | **Main orchestrator** — coordinates all execution |
| Engine | [engine/playbook.py](src/sansible/engine/playbook.py) | YAML parsing, FQCN normalization (`ansible.builtin.copy` → `copy`) |
| Engine | [engine/templating.py](src/sansible/engine/templating.py) | Jinja2 with `StrictUndefined` |
| Connections | [connections/base.py](src/sansible/connections/base.py) | ABC: `connect()`, `run()`, `put()`, `stat()` |
| Modules | [modules/base.py](src/sansible/modules/base.py) | `@register_module` decorator and `Module` base class |

**Execution model:** Linear strategy — for each task, run on all hosts concurrently (up to `--forks`) → next task.

## Developer Workflow

```bash
pip install -e ".[dev]"           # Includes ansible-core for golden tests
pytest tests/unit/ -q             # Fast unit tests (310 tests, no network)
pytest tests/golden/ -v           # Compare output vs real ansible-playbook
sansible-playbook -i examples/inventory.ini examples/linux_playbook.yml
```

## Adding a Module

Create `src/sansible/modules/builtin_<name>.py`:

```python
from sansible.modules.base import Module, ModuleResult, register_module

@register_module
class MyModule(Module):
    name = "my_module"
    required_args = ["dest"]
    optional_args = {"force": True}

    async def run(self) -> ModuleResult:
        # self.connection.run(), self.connection.put(), self.context.check_mode
        return ModuleResult(changed=True, msg="done")
```

Import it in [modules/base.py](src/sansible/modules/base.py) → `_import_builtin_modules()`.

## Adding a Connection

Implement `Connection` ABC from [connections/base.py](src/sansible/connections/base.py):
- Required: `connect()`, `close()`, `run()`, `put()`, `get()`, `mkdir()`, `stat()`

Register in [engine/runner.py](src/sansible/engine/runner.py) → `_get_connection_class()`.

## Error Handling

Use exceptions from [engine/errors.py](src/sansible/engine/errors.py):

| Exception | Exit Code | When |
|-----------|-----------|------|
| `ParseError` | 3 | Invalid inventory/playbook YAML |
| `UnsupportedFeatureError` | 4 | Feature outside supported subset |
| `ModuleError` | 2 | Module execution failure |

## Key Conventions

1. **All modules are async** — `async def run()` using `await`
2. **Jinja2 StrictUndefined** — undefined variables raise immediately
3. **Exit codes**: 0=success, 2=host failure, 3=parse error, 4=unsupported
4. **Extras**: `[ssh]` asyncssh, `[winrm]` pypsrp, `[vault]` cryptography
5. **Mock connections in tests** — see `MockConnection` in [test_executor_linear.py](tests/unit/test_executor_linear.py)

## Testing Patterns

| Type | Location | Description |
|------|----------|-------------|
| Unit | `tests/unit/` | Mock connections, no network |
| Golden | `tests/golden/` | JSON comparison vs `ansible-playbook` |
| Integration | `tests/integration/` | Docker SSH containers |

## Out of Scope

Raise `UnsupportedFeatureError` for: `async/poll`, Galaxy collections, complex lookups.
- Ad-hoc `sansible` and `sansible-inventory` CLIs are placeholders; playbook CLI is the supported path.

## Supported Modules (61 total)

- **Linux (45)**: `command`, `shell`, `copy`, `file`, `template`, `lineinfile`, `stat`, `setup`, `debug`, `set_fact`, etc.
- **Windows (16)**: `win_command`, `win_shell`, `win_copy`, `win_file`, `win_service`, `win_stat`, etc.

See full list in [docs/MODULES.md](docs/MODULES.md).

## Testing Workflow

### Quick Validation
```bash
python -m build --wheel
pip install dist/sansible-*.whl --force-reinstall
pytest tests/unit/ -q --tb=no  # 307 tests
```

### Production Testing (Linux)
```bash
sansible-playbook -i tests/e2e/live_inventory.ini tests/e2e/test_all_linux_modules.yml -v
# Expected: ok=35 changed=25 failed=2 skipped=2
```

### Production Testing (Windows)
```bash
sansible-playbook -i tests/e2e/live_inventory.ini tests/e2e/test_all_windows_modules.yml -v
# Expected: ok=28 changed=17 failed=1
```

See [.github/TESTING_LINUX.md](.github/TESTING_LINUX.md) and [.github/TESTING_WINDOWS.md](.github/TESTING_WINDOWS.md) for full AI agent testing prompts.

## Reference Docs

| Document | Purpose |
|----------|---------|
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Developer quick start guide |
| [docs/MODULES.md](docs/MODULES.md) | Complete module reference |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/REFACTORING.md](docs/REFACTORING.md) | Code improvement recommendations |
| [docs/TESTING.md](docs/TESTING.md) | Test strategy |
