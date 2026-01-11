# Test Documentation

This document describes the testing strategy and how to run tests for sansible.

## Test Categories

### 1. Unit Tests
Location: `tests/unit/`  
Runner: pytest  
Purpose: Test individual functions and classes in isolation

### 2. Integration Tests
Location: `tests/integration/`  
Runner: pytest  
Purpose: Test component interactions

### 3. Smoke Tests
Location: `tools/`  
Runner: Direct Python execution  
Purpose: Verify basic functionality on each platform

### 4. Acceptance Tests
Location: `tests/acceptance/`  
Runner: sansible itself  
Purpose: Verify end-to-end functionality with real playbooks

---

## Running Tests

### Quick Smoke Tests

```bash
# Linux
python -m tools.linux_smoke

# Windows (PowerShell)
python -m tools.windows_smoke
```

### Full Test Suite

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=sansible --cov-report=html
```

### Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_inventory.py

# Specific test
pytest tests/unit/test_inventory.py::test_parse_ini
```

---

## Pure Python Audit

```bash
# Full audit (builds wheel, installs, checks)
python -m tools.dep_audit

# Check existing wheel
python -m tools.dep_audit --check-wheel dist/sansible-*.whl
```

---

## Acceptance Test Environment

### Local Testing

```yaml
# tests/acceptance/inventory.ini
[local]
localhost ansible_connection=local

[linux]
testhost ansible_host=192.168.1.100 ansible_user=testuser

[windows]
winhost ansible_host=192.168.1.101 ansible_connection=winrm
```

### Test Playbooks

```bash
# Test localhost execution
sansible-playbook -i tests/acceptance/inventory.ini tests/acceptance/play_local.yml

# Test SSH (requires configured target)
sansible-playbook -i tests/acceptance/inventory.ini tests/acceptance/play_ssh.yml -l linux

# Test WinRM (requires configured target)
sansible-playbook -i tests/acceptance/inventory.ini tests/acceptance/play_winrm.yml -l windows
```

---

## Test Matrix

### Platform Matrix

| Platform | Python Versions | Status |
|----------|-----------------|--------|
| Ubuntu 22.04 | 3.9, 3.10, 3.11, 3.12 | Primary |
| Windows 10 | 3.9, 3.10, 3.11, 3.12 | Primary |
| Windows 11 | 3.11, 3.12 | Secondary |
| macOS 13 | 3.10, 3.11, 3.12 | Secondary |

### Feature Matrix

| Feature | Unit | Integration | Acceptance |
|---------|------|-------------|------------|
| CLI parsing | ✓ | ✓ | ✓ |
| INI inventory | ✓ | ✓ | ✓ |
| YAML inventory | ✓ | ✓ | ✓ |
| Localhost | ✓ | ✓ | ✓ |
| SSH transport | - | ✓ | ✓ |
| WinRM transport | - | ✓ | ✓ |
| Concurrency | ✓ | ✓ | ✓ |

---

## Writing Tests

### Unit Test Example

```python
# tests/unit/test_paths.py
import pytest
from sansible.platform import paths

def test_normalize_path():
    result = paths.normalize("foo/bar/../baz")
    assert ".." not in result

def test_to_posix():
    assert paths.to_posix("foo\\bar") == "foo/bar"

@pytest.mark.parametrize("input,expected", [
    (".", "."),
    ("./foo", "foo"),
    ("foo/../bar", "bar"),
])
def test_normalize_cases(input, expected):
    assert paths.normalize(input) == expected
```

### Integration Test Example

```python
# tests/integration/test_inventory.py
import pytest
from sansible.inventory import parse_inventory

@pytest.fixture
def sample_ini(tmp_path):
    ini_file = tmp_path / "inventory.ini"
    ini_file.write_text("""
[webservers]
web1 ansible_host=192.168.1.10
web2 ansible_host=192.168.1.11

[databases]
db1 ansible_host=192.168.1.20
""")
    return ini_file

def test_parse_ini_groups(sample_ini):
    inv = parse_inventory(sample_ini)
    assert "webservers" in inv.groups
    assert "databases" in inv.groups
```

---

## CI Configuration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        python: ['3.9', '3.10', '3.11', '3.12']
    
    runs-on: ${{ matrix.os }}
    
    steps:
    - uses: actions/checkout@v4
    
    - uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python }}
    
    - name: Install dependencies
      run: pip install -e ".[dev]"
    
    - name: Run smoke tests
      run: |
        python -m tools.windows_smoke
      if: runner.os == 'Windows'
    
    - name: Run smoke tests
      run: python -m tools.linux_smoke
      if: runner.os == 'Linux'
    
    - name: Run pytest
      run: pytest --cov=sansible
    
    - name: Run dep audit
      run: python -m tools.dep_audit
```

---

## Troubleshooting

### Test Discovery Issues
```bash
# Check pytest can find tests
pytest --collect-only
```

### Import Errors
```bash
# Ensure package is installed
pip install -e .
python -c "import sansible; print(sansible.__version__)"
```

### Platform-Specific Failures
```bash
# Check platform detection
python -c "from sansible.platform import IS_WINDOWS; print(f'Windows: {IS_WINDOWS}')"
```
