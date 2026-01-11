# Sansible Development Guide

> **Version**: 0.4.0 (ModuleStorm)  
> **Last Updated**: January 2026

## Quick Start

```bash
# Clone and setup
git clone https://github.com/small-ansible/sansible.git
cd sansible
pip install -e ".[dev]"

# Run tests
pytest tests/unit/ -q        # 307 tests, ~2s
pytest tests/golden/ -v      # Compare with real ansible-playbook

# Run example playbook
sansible-playbook -i examples/inventory.ini examples/linux_playbook.yml
```

## Project Structure

```
sansible/
├── src/sansible/           # Main package
│   ├── cli/                # Command-line interface
│   │   ├── playbook.py     # sansible-playbook entrypoint
│   │   ├── inventory.py    # sansible-inventory (placeholder)
│   │   └── main.py         # sansible (placeholder)
│   ├── engine/             # Core execution engine
│   │   ├── runner.py       # PlaybookRunner orchestrator
│   │   ├── playbook.py     # YAML parser, FQCN normalization
│   │   ├── inventory.py    # Inventory management
│   │   ├── templating.py   # Jinja2 with StrictUndefined
│   │   ├── scheduler.py    # Async task scheduling
│   │   └── errors.py       # Exception hierarchy
│   ├── connections/        # Transport implementations
│   │   ├── base.py         # Abstract Connection class
│   │   ├── local.py        # Local subprocess execution
│   │   ├── ssh_asyncssh.py # SSH via asyncssh
│   │   └── winrm_psrp.py   # WinRM via pypsrp
│   ├── modules/            # 61 Ansible-compatible modules
│   │   ├── base.py         # Module base class & registry
│   │   ├── builtin_*.py    # Linux modules
│   │   └── win_*.py        # Windows modules
│   ├── inventory/          # Inventory parsing
│   ├── platform/           # Cross-platform utilities
│   └── galaxy/             # Galaxy FQCN support
├── tests/                  # Test suites
│   ├── unit/               # Unit tests (307 tests)
│   ├── golden/             # Comparison with ansible-playbook
│   ├── integration/        # Docker-based integration tests
│   └── e2e/                # End-to-end test playbooks
├── examples/               # Example playbooks
└── docs/                   # Documentation
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    sansible-playbook CLI                     │
│              (cli/playbook.py - argparse)                    │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                     PlaybookRunner                           │
│                   (engine/runner.py)                         │
│  • Load inventory & playbooks                                │
│  • Coordinate connections                                    │
│  • Execute tasks with block/rescue/always                    │
│  • Handle handlers & output                                  │
└──────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
│  LocalConnection │ │SSHConnection │ │  WinRMConnection │
│   (local.py)     │ │(asyncssh)    │ │    (pypsrp)      │
└──────────────────┘ └──────────────┘ └──────────────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                      Module Execution                        │
│  • 45 Linux modules (builtin_*.py)                          │
│  • 16 Windows modules (win_*.py)                            │
│  • Galaxy FQCN normalization                                │
└──────────────────────────────────────────────────────────────┘
```

## Adding a New Module

### Linux Module

```python
# src/sansible/modules/builtin_mymodule.py
from sansible.modules.base import Module, ModuleResult, register_module

@register_module
class MyModule(Module):
    name = "mymodule"
    required_args = ["path"]
    optional_args = {"force": False}
    
    async def run(self) -> ModuleResult:
        if not self.connection:
            return ModuleResult(failed=True, msg="No connection")
        
        if self.context.check_mode:
            return ModuleResult(changed=True, msg="Would do action")
        
        result = await self.connection.run(f"somecommand {self.args['path']}")
        
        return ModuleResult(
            changed=True,
            msg="Action completed",
            results={"output": result.stdout},
        )
```

Register in `modules/base.py`:
```python
def _import_builtin_modules():
    ...
    from sansible.modules import builtin_mymodule
```

### Windows Module

Same pattern with `win_` prefix and PowerShell commands.

## Adding a Connection Type

Implement the `Connection` abstract base class:

```python
# src/sansible/connections/myconnection.py
from sansible.connections.base import Connection, RunResult

class MyConnection(Connection):
    async def connect(self) -> None:
        """Establish connection."""
        pass
    
    async def close(self) -> None:
        """Close connection."""
        pass
    
    async def run(self, command: str, **kwargs) -> RunResult:
        """Execute command and return result."""
        pass
    
    async def put(self, local_path: str, remote_path: str) -> None:
        """Upload file."""
        pass
    
    async def get(self, remote_path: str, local_path: str) -> None:
        """Download file."""
        pass
```

Register in `engine/runner.py` → `_create_connection()`.

## Testing

### Unit Tests
```bash
pytest tests/unit/ -v              # All unit tests
pytest tests/unit/test_runner.py   # Specific file
pytest -k "test_copy"              # Pattern matching
```

### Golden Tests (vs real Ansible)
```bash
pytest tests/golden/ -v
```

### End-to-End Tests
```bash
# Create inventory with real targets
cat > tests/e2e/test_inventory.ini << 'INV'
[linux]
target ansible_host=IP ansible_user=USER ansible_password=PASS ansible_connection=ssh

[windows]
target ansible_host=IP ansible_user=USER ansible_password=PASS ansible_connection=winrm
INV

sansible-playbook -i tests/e2e/test_inventory.ini tests/e2e/test_linux_core.yml
```

## Error Handling

Use exceptions from `engine/errors.py`:

| Exception | Exit Code | When |
|-----------|-----------|------|
| `ParseError` | 3 | Invalid YAML syntax |
| `UnsupportedFeatureError` | 4 | Feature outside scope |
| `ModuleError` | 2 | Module execution failure |
| `ConnectionError` | 2 | Connection failure |

## Code Style

- **Formatter**: `ruff format`
- **Linter**: `ruff check`
- **Type checking**: `mypy src/sansible`
- **Line length**: 100 characters
- **All modules are async**: Use `async def run()`
- **Jinja2**: StrictUndefined (undefined vars raise immediately)

## Release Process

1. Update version in `src/sansible/release.py`
2. Update `CHANGELOG.md`
3. Run full test suite
4. Build wheel: `python -m build`
5. Test wheel: `pip install dist/*.whl`
6. Tag release: `git tag v0.x.0`
7. Push: `git push && git push --tags`

## Key Conventions

1. **Pure Python wheel** (`py3-none-any`) - no compiled extensions
2. **Windows-native control node** - no WSL required
3. **Fail fast** with `UnsupportedFeatureError` for unsupported features
4. **Linear strategy** - for each task, run on all hosts → next task
5. **Exit codes**: 0=success, 2=host failure, 3=parse error, 4=unsupported
