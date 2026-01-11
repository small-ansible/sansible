# Testing Sansible

This document describes how to run tests for Sansible.

## Quick Start

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=sansible --cov-report=term-missing
```

## Test Structure

```
tests/
├── unit/                    # Unit tests (no external deps)
│   ├── test_inventory.py    # Inventory parsing
│   ├── test_playbook.py     # Playbook parsing
│   ├── test_templating.py   # Jinja2 templating
│   └── test_scheduler.py    # Scheduler logic
├── integration/             # Integration tests
│   ├── test_local.py        # Localhost execution
│   ├── test_ssh.py          # SSH connection (needs Docker)
│   └── test_winrm.py        # WinRM connection (needs Windows)
└── fixtures/                # Test data
    ├── inventory.ini        # Sample inventory
    └── playbooks/           # Sample playbooks
        ├── linux_smoke.yml
        ├── windows_smoke.yml
        └── mixed_smoke.yml
```

## Unit Tests

Unit tests run without external dependencies:

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_inventory.py -v

# Run specific test
pytest tests/unit/test_inventory.py::TestInventoryParser::test_parse_ini -v

# Run with verbose output
pytest tests/unit/ -v --tb=long
```

## Integration Tests

### Local Execution

Tests localhost execution without network:

```bash
pytest tests/integration/test_local.py -v
```

### SSH Tests (Docker)

SSH tests require a running Docker container with SSH:

```bash
# Start SSH container
docker run -d --name sansible-ssh-test \
  -p 2222:22 \
  rastasheep/ubuntu-sshd:18.04

# Run SSH tests
pytest tests/integration/test_ssh.py -v

# Cleanup
docker rm -f sansible-ssh-test
```

### WinRM Tests

WinRM tests require a Windows target with WinRM enabled.

**On Windows (local testing):**

```powershell
# Enable WinRM
Enable-PSRemoting -Force

# Allow unencrypted for testing (not for production!)
Set-Item WSMan:\localhost\Service\AllowUnencrypted $true

# Run tests
$env:NEO_WINRM_HOST = "localhost"
$env:NEO_WINRM_USER = "Administrator"
$env:NEO_WINRM_PASSWORD = "YourPassword"
pytest tests/integration/test_winrm.py -v
```

**Skip WinRM tests:**

```bash
pytest tests/integration/ -v --ignore=tests/integration/test_winrm.py
```

## Golden Tests

Golden tests compare Sansible output with real Ansible:

```bash
# Run golden tests (requires ansible-core installed)
pytest tests/golden/ -v

# Update golden baselines
pytest tests/golden/ -v --update-golden
```

Requirements:
- `ansible-core` must be installed
- Same inventory and playbooks used for both

## Markers

```bash
# Skip slow tests
pytest -v -m "not slow"

# Run only Windows tests
pytest -v -m windows

# Run only SSH tests
pytest -v -m ssh
```

Available markers:
- `slow`: Long-running tests
- `windows`: Requires Windows target
- `ssh`: Requires SSH target
- `docker`: Requires Docker

## Coverage

```bash
# Generate coverage report
pytest tests/unit/ --cov=sansible --cov-report=html

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## CI/CD

GitHub Actions workflow runs:

1. Unit tests (all platforms)
2. Lint checks (ruff)
3. Type checks (mypy)
4. SSH integration tests (Linux, Docker)
5. WinRM integration tests (Windows runner)

See `.github/workflows/ci.yml` for details.

## Writing Tests

### Unit Test Template

```python
import pytest
from sansible.engine.inventory import InventoryManager

class TestInventoryParser:
    def test_parse_simple_host(self):
        """Test parsing a single host."""
        inv = InventoryManager()
        inv._parse_ini_string("host1.example.com")
        
        assert "host1.example.com" in inv.hosts
        assert inv.hosts["host1.example.com"].name == "host1.example.com"
    
    def test_parse_with_vars(self):
        """Test parsing host with inline variables."""
        inv = InventoryManager()
        inv._parse_ini_string("host1 ansible_user=admin ansible_port=2222")
        
        host = inv.hosts["host1"]
        assert host.ansible_user == "admin"
        assert host.ansible_port == 2222
```

### Integration Test Template

```python
import pytest
import asyncio
from pathlib import Path

from sansible.engine.inventory import InventoryManager
from sansible.engine.playbook import PlaybookParser
from sansible.engine.scheduler import Scheduler
from sansible.connections import create_connection_factory
from sansible.modules import create_module_runner

@pytest.mark.integration
class TestLocalExecution:
    @pytest.fixture
    def inventory(self):
        inv = InventoryManager()
        inv._parse_ini_string("localhost ansible_connection=local")
        return inv
    
    @pytest.fixture
    def playbook_path(self):
        return Path(__file__).parent.parent / "fixtures" / "playbooks" / "linux_smoke.yml"
    
    @pytest.mark.asyncio
    async def test_run_smoke_playbook(self, inventory, playbook_path):
        """Test running the smoke playbook locally."""
        parser = PlaybookParser(playbook_path)
        plays = parser.parse()
        
        hosts = inventory.get_hosts("localhost")
        connection_factory = create_connection_factory()
        module_runner = create_module_runner()
        
        scheduler = Scheduler(forks=1, connection_factory=connection_factory)
        result = await scheduler.run_playbook(
            plays=plays,
            hosts=hosts,
            playbook_path=str(playbook_path),
            module_runner=module_runner,
        )
        
        assert result.success
```

## Debugging Tests

```bash
# Drop into debugger on failure
pytest tests/unit/ -v --pdb

# Print stdout/stderr
pytest tests/unit/ -v -s

# Increase verbosity
pytest tests/unit/ -vvv

# Run specific test with debugging
pytest tests/unit/test_inventory.py::test_parse_ini -v -s --pdb
```

## Performance Testing

```bash
# Time tests
pytest tests/unit/ -v --durations=10

# Profile tests
pytest tests/unit/ --profile

# Run with parallel workers
pytest tests/unit/ -n auto  # Requires pytest-xdist
```
