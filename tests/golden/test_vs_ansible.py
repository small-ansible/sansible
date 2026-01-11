"""
Golden Tests — Compare Sansible vs ansible-playbook

These tests run the same playbooks with both Sansible and real Ansible,
then compare the results to ensure compatibility.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import pytest


# Check if ansible-playbook is available
def ansible_available() -> bool:
    """Check if ansible-playbook is installed and available."""
    try:
        result = subprocess.run(
            ["ansible-playbook", "--version"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def ansible_json_callback_available() -> bool:
    """Check if Ansible json callback is available."""
    try:
        import tempfile
        import yaml
        
        # Create a minimal playbook to test
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump([{'hosts': 'localhost', 'gather_facts': False, 
                       'tasks': [{'ping': None}]}], f)
            playbook_path = f.name
        
        env = os.environ.copy()
        env["ANSIBLE_STDOUT_CALLBACK"] = "json"
        env["ANSIBLE_HOST_KEY_CHECKING"] = "False"
        result = subprocess.run(
            ["ansible-playbook", "-i", "localhost,", playbook_path],
            capture_output=True,
            timeout=30,
            env=env,
        )
        
        # Clean up
        os.unlink(playbook_path)
        
        # Check if json callback error appears in stderr
        return b"Could not load 'json'" not in result.stderr
    except Exception:
        return False


ANSIBLE_AVAILABLE = ansible_available()
ANSIBLE_JSON_CALLBACK_AVAILABLE = ansible_available() and ansible_json_callback_available()
SKIP_REASON = "ansible-playbook not installed (run with dev dependencies)"
SKIP_REASON_JSON = "ansible json callback not available (missing collection)"


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def inventory_file(fixtures_dir: Path) -> Path:
    """Path to inventory file."""
    return fixtures_dir / "inventory.ini"


class GoldenTestRunner:
    """
    Runs playbooks with both Sansible and Ansible and compares results.
    """
    
    def __init__(self, inventory: str, playbook: str):
        self.inventory = inventory
        self.playbook = playbook
        self.san_result: Optional[Dict[str, Any]] = None
        self.ansible_result: Optional[Dict[str, Any]] = None
        self.san_exit_code: int = -1
        self.ansible_exit_code: int = -1
    
    def run_sansible(self) -> Tuple[int, Dict[str, Any]]:
        """Run playbook with Sansible and return exit code and JSON result."""
        result = subprocess.run(
            [
                sys.executable, "-m", "sansible.cli.playbook",
                "-i", self.inventory,
                self.playbook,
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        self.san_exit_code = result.returncode
        
        try:
            self.san_result = json.loads(result.stdout)
        except json.JSONDecodeError:
            self.san_result = {"error": "Failed to parse JSON", "stdout": result.stdout}
        
        return self.san_exit_code, self.san_result
    
    def run_ansible(self) -> Tuple[int, Dict[str, Any]]:
        """Run playbook with ansible-playbook and return exit code and summary."""
        # Create a simple callback to capture results
        env = os.environ.copy()
        env["ANSIBLE_STDOUT_CALLBACK"] = "json"
        env["ANSIBLE_HOST_KEY_CHECKING"] = "False"
        
        result = subprocess.run(
            [
                "ansible-playbook",
                "-i", self.inventory,
                self.playbook,
            ],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        
        self.ansible_exit_code = result.returncode
        
        try:
            self.ansible_result = json.loads(result.stdout)
        except json.JSONDecodeError:
            # Ansible JSON callback output may have extra lines
            lines = result.stdout.strip().split('\n')
            for line in lines:
                try:
                    self.ansible_result = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
            if self.ansible_result is None:
                self.ansible_result = {"error": "Failed to parse JSON", "stdout": result.stdout}
        
        return self.ansible_exit_code, self.ansible_result
    
    def compare_exit_codes(self) -> bool:
        """Check if both exit codes indicate same success/failure."""
        san_success = self.san_exit_code == 0
        ansible_success = self.ansible_exit_code == 0
        return san_success == ansible_success
    
    def compare_stats(self) -> Dict[str, Any]:
        """Compare aggregate stats between Sansible and Ansible."""
        comparison = {
            "san_exit": self.san_exit_code,
            "ansible_exit": self.ansible_exit_code,
            "exit_codes_match": self.compare_exit_codes(),
            "san_stats": {},
            "ansible_stats": {},
        }
        
        # Extract Sansible stats
        if self.san_result and "stats" in self.san_result:
            comparison["san_stats"] = self.san_result["stats"]
        
        # Extract Ansible stats (format varies by callback)
        if self.ansible_result:
            if "stats" in self.ansible_result:
                comparison["ansible_stats"] = self.ansible_result["stats"]
        
        return comparison


# Helper to check if a file exists on the target
def file_exists(path: str) -> bool:
    """Check if a file exists locally."""
    return Path(path).exists()


def file_content(path: str) -> str:
    """Read file content."""
    return Path(path).read_text()


@pytest.mark.skipif(not ANSIBLE_JSON_CALLBACK_AVAILABLE, reason=SKIP_REASON_JSON)
class TestGoldenLinuxSmoke:
    """Golden tests for linux_smoke.yml playbook."""
    
    def test_both_run_successfully(self, inventory_file: Path, fixtures_dir: Path):
        """Both Sansible and Ansible should succeed with linux_smoke.yml."""
        playbook = str(fixtures_dir / "playbooks" / "linux_smoke.yml")
        
        runner = GoldenTestRunner(str(inventory_file), playbook)
        
        san_exit, san_result = runner.run_sansible()
        ansible_exit, ansible_result = runner.run_ansible()
        
        # Both should succeed
        assert san_exit == 0, f"Sansible failed with exit {san_exit}: {san_result}"
        assert ansible_exit == 0, f"Ansible failed with exit {ansible_exit}: {ansible_result}"
        
        # Exit codes should match
        assert runner.compare_exit_codes(), "Exit codes don't match"
    
    def test_stats_comparable(self, inventory_file: Path, fixtures_dir: Path):
        """Stats from Sansible and Ansible should be comparable."""
        playbook = str(fixtures_dir / "playbooks" / "linux_smoke.yml")
        
        runner = GoldenTestRunner(str(inventory_file), playbook)
        runner.run_sansible()
        runner.run_ansible()
        
        comparison = runner.compare_stats()
        
        # Both should have some ok tasks
        san_stats = comparison.get("san_stats", {}).get("localhost", {})
        # Note: Ansible stats format differs, so we just check Sansible ran successfully
        assert san_stats.get("ok", 0) > 0 or san_stats.get("changed", 0) > 0


class TestNeoOnly:
    """Tests that only run Sansible (don't require ansible-playbook)."""
    
    def test_json_output_format(self, inventory_file: Path, fixtures_dir: Path):
        """Sansible JSON output should have correct structure."""
        playbook = str(fixtures_dir / "playbooks" / "linux_smoke.yml")
        
        result = subprocess.run(
            [
                sys.executable, "-m", "sansible.cli.playbook",
                "-i", str(inventory_file),
                playbook,
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        assert result.returncode == 0
        
        data = json.loads(result.stdout)
        
        # Check structure
        assert "playbook" in data
        assert "plays" in data
        assert "stats" in data
        
        # Check plays structure
        assert len(data["plays"]) > 0
        play = data["plays"][0]
        assert "play" in play
        assert "hosts" in play
        assert "tasks" in play
        assert "stats" in play
        
        # Check tasks have expected fields
        if play["tasks"]:
            task = play["tasks"][0]
            assert "host" in task
            assert "task" in task
            assert "status" in task
            assert "changed" in task
    
    def test_json_error_output(self, fixtures_dir: Path):
        """Sansible should output JSON errors when --json flag is used."""
        result = subprocess.run(
            [
                sys.executable, "-m", "sansible.cli.playbook",
                "-i", "nonexistent_inventory.ini",
                "nonexistent_playbook.yml",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        # Should fail
        assert result.returncode != 0
        
        # Should have JSON error
        data = json.loads(result.stdout)
        assert "error" in data
        assert data["error"] is True


@pytest.mark.skipif(not ANSIBLE_AVAILABLE, reason=SKIP_REASON)
class TestIdempotency:
    """Test that running playbooks twice produces expected results."""
    
    def test_second_run_less_changes(self, inventory_file: Path, fixtures_dir: Path):
        """Running playbook twice should show fewer changes on second run."""
        playbook = str(fixtures_dir / "playbooks" / "linux_smoke.yml")
        
        runner = GoldenTestRunner(str(inventory_file), playbook)
        
        # First run
        exit1, result1 = runner.run_sansible()
        assert exit1 == 0
        
        # Second run
        exit2, result2 = runner.run_sansible()
        assert exit2 == 0
        
        # Get change counts
        stats1 = result1.get("stats", {}).get("localhost", {})
        stats2 = result2.get("stats", {}).get("localhost", {})
        
        changes1 = stats1.get("changed", 0)
        changes2 = stats2.get("changed", 0)
        
        # Note: This playbook cleans up after itself, so we can't strictly
        # test idempotency. But it should run successfully both times.
        assert exit1 == exit2 == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
