"""
Golden Tests Fixtures and Configuration
"""

import pytest
from pathlib import Path


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def fixtures_dir(project_root: Path) -> Path:
    """Return the fixtures directory."""
    return project_root / "tests" / "fixtures"


@pytest.fixture
def playbooks_dir(fixtures_dir: Path) -> Path:
    """Return the playbooks directory."""
    return fixtures_dir / "playbooks"
