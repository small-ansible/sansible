# Contributing to Sansible

Thank you for your interest in contributing to Sansible!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/sansible/sansible.git
cd sansible

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"

# Verify installation
san --version
pytest tests/unit/ -v
```

## Project Structure

```
src/sansible/
├── cli/                 # Command-line interface
├── connections/         # SSH, WinRM, local connections
├── engine/              # Core execution engine
│   ├── playbook.py      # YAML parsing
│   ├── scheduler.py     # Parallel execution
│   ├── templating.py    # Jinja2 templating
│   └── runner.py        # Main orchestrator
└── modules/             # Built-in modules
    ├── builtin_*.py     # Linux modules
    └── win_*.py         # Windows modules
```

## Running Tests

```bash
# Unit tests (fast, no network)
pytest tests/unit/ -v

# Golden tests (compare Sansible vs Ansible output)
pytest tests/golden/ -v

# Integration tests (requires Docker)
pytest tests/integration/ -v

# All tests with coverage
pytest --cov=sansible --cov-report=html
```

## Adding a New Module

1. Create `src/sansible/modules/builtin_<name>.py`:

```python
from sansible.modules.base import Module, ModuleResult, register_module

@register_module
class MyModule(Module):
    name = "my_module"
    required_args = ["dest"]
    optional_args = {"force": True}

    async def run(self) -> ModuleResult:
        # Implementation
        return ModuleResult(changed=True, msg="done")
```

2. Import in `src/sansible/modules/base.py` → `_import_builtin_modules()`

3. Add tests in `tests/unit/test_<name>_module.py`

## Code Style

- Use `ruff` for linting: `ruff check src/`
- Use `ruff format` for formatting: `ruff format src/`
- Use type hints for all public functions
- Maximum line length: 100 characters

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Write tests for your changes
4. Ensure all tests pass (`pytest tests/unit/ -v`)
5. Update documentation if needed
6. Submit a pull request

## Commit Messages

Use conventional commits:

- `feat: add win_registry module`
- `fix: handle empty inventory files`
- `docs: update README examples`
- `test: add coverage for block parsing`
- `refactor: simplify templating logic`

## Constraints

Remember the project constraints:

1. **Pure Python Wheel**: No compiled extensions
2. **Windows Native**: Must work on Windows without WSL
3. **Minimal Dependencies**: Core only needs PyYAML + Jinja2
4. **Fail Fast**: Unsupported features raise `UnsupportedFeatureError`

## Questions?

Open an issue on GitHub for questions or discussions.
