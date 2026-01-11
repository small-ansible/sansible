"""
SSH Integration Tests

Tests that run playbooks against a real SSH server in Docker.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Generator, Optional

import pytest

# Check if docker is available
def docker_available() -> bool:
    """Check if Docker is installed and running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# Check if asyncssh is available
def asyncssh_available() -> bool:
    """Check if asyncssh is installed."""
    try:
        import asyncssh
        return True
    except ImportError:
        return False


DOCKER_AVAILABLE = docker_available()
ASYNCSSH_AVAILABLE = asyncssh_available()
SKIP_DOCKER = "Docker not available or not running"
SKIP_ASYNCSSH = "asyncssh not installed (pip install sansible[ssh])"


class SSHTestContainer:
    """Manage an SSH container for testing."""
    
    CONTAINER_NAME = "sansible-ssh-test"
    IMAGE_NAME = "sansible-ssh-test"
    SSH_PORT = 2222
    SSH_USER = "testuser"
    SSH_PASS = "testpass"
    
    def __init__(self):
        self.container_id: Optional[str] = None
        self.dockerfile_path = Path(__file__).parent / "docker" / "Dockerfile.ssh"
    
    def build(self) -> bool:
        """Build the SSH test container image."""
        result = subprocess.run(
            [
                "docker", "build",
                "-t", self.IMAGE_NAME,
                "-f", str(self.dockerfile_path),
                str(self.dockerfile_path.parent),
            ],
            capture_output=True,
            timeout=120,
        )
        return result.returncode == 0
    
    def start(self) -> bool:
        """Start the SSH test container."""
        # Stop any existing container
        self.stop()
        
        # Start new container
        result = subprocess.run(
            [
                "docker", "run",
                "-d",
                "--name", self.CONTAINER_NAME,
                "-p", f"{self.SSH_PORT}:22",
                self.IMAGE_NAME,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode != 0:
            return False
        
        self.container_id = result.stdout.strip()
        
        # Wait for SSH to be ready
        return self._wait_for_ssh()
    
    def _wait_for_ssh(self, timeout: int = 30) -> bool:
        """Wait for SSH server to be ready."""
        start = time.time()
        while time.time() - start < timeout:
            result = subprocess.run(
                [
                    "docker", "exec", self.CONTAINER_NAME,
                    "nc", "-z", "localhost", "22",
                ],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                # Give it a moment more to fully initialize
                time.sleep(1)
                return True
            time.sleep(0.5)
        return False
    
    def stop(self) -> None:
        """Stop and remove the container."""
        subprocess.run(
            ["docker", "rm", "-f", self.CONTAINER_NAME],
            capture_output=True,
            timeout=30,
        )
        self.container_id = None
    
    def get_inventory_content(self) -> str:
        """Generate inventory content for the container."""
        return f"""[ssh_targets]
sshtest ansible_host=127.0.0.1 ansible_port={self.SSH_PORT} ansible_user={self.SSH_USER} ansible_password={self.SSH_PASS} ansible_connection=ssh ansible_ssh_host_key_checking=false
"""


@pytest.fixture(scope="module")
def ssh_container() -> Generator[SSHTestContainer, None, None]:
    """Start SSH container for tests."""
    container = SSHTestContainer()
    
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_DOCKER)
    
    # Build image
    if not container.build():
        pytest.skip("Failed to build SSH test container")
    
    # Start container
    if not container.start():
        container.stop()
        pytest.skip("Failed to start SSH test container")
    
    yield container
    
    # Cleanup
    container.stop()


@pytest.fixture
def ssh_inventory(ssh_container: SSHTestContainer, tmp_path: Path) -> Path:
    """Create inventory file for SSH container."""
    inventory_file = tmp_path / "inventory.ini"
    inventory_file.write_text(ssh_container.get_inventory_content())
    return inventory_file


@pytest.fixture
def ssh_playbook(tmp_path: Path) -> Path:
    """Create a simple SSH test playbook."""
    playbook_content = """---
- name: SSH Integration Test
  hosts: ssh_targets
  gather_facts: false
  
  tasks:
    - name: Check connectivity with raw command
      raw: echo "Hello from SSH"
      register: hello_result
    
    - name: Assert connection works
      assert:
        that:
          - hello_result.stdout is defined
          - "'Hello' in hello_result.stdout"
    
    - name: Create a test file
      shell: echo "Sansible was here" > /tmp/sansible_test_file.txt
    
    - name: Read test file
      command: cat /tmp/sansible_test_file.txt
      register: file_content
    
    - name: Verify file content
      assert:
        that:
          - "Sansible in file_content.stdout"
    
    - name: Cleanup test file
      shell: rm -f /tmp/sansible_test_file.txt
"""
    playbook_file = tmp_path / "ssh_test.yml"
    playbook_file.write_text(playbook_content)
    return playbook_file


@pytest.mark.skipif(not DOCKER_AVAILABLE, reason=SKIP_DOCKER)
@pytest.mark.skipif(not ASYNCSSH_AVAILABLE, reason=SKIP_ASYNCSSH)
class TestSSHIntegration:
    """SSH integration tests with Docker container."""
    
    def test_ssh_raw_command(self, ssh_inventory: Path, tmp_path: Path):
        """Test raw command execution over SSH."""
        playbook_content = """---
- name: Raw SSH Test
  hosts: ssh_targets
  gather_facts: false
  tasks:
    - name: Run raw command
      raw: echo "Success from SSH"
      register: result
    
    - name: Show result
      debug:
        var: result
"""
        playbook = tmp_path / "test.yml"
        playbook.write_text(playbook_content)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "sansible.san_cli",
                "run",
                "-i", str(ssh_inventory),
                str(playbook),
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        assert result.returncode == 0, f"Failed: {result.stdout}\n{result.stderr}"
        
        import json
        data = json.loads(result.stdout)
        assert data.get("stats", {}).get("sshtest", {}).get("failed", 1) == 0
    
    def test_ssh_shell_command(self, ssh_inventory: Path, tmp_path: Path):
        """Test shell command execution over SSH."""
        playbook_content = """---
- name: Shell SSH Test
  hosts: ssh_targets
  gather_facts: false
  tasks:
    - name: Run shell command
      shell: echo "Hello" && echo "World"
      register: result
    
    - name: Check output
      assert:
        that:
          - "'Hello' in result.stdout"
          - "'World' in result.stdout"
"""
        playbook = tmp_path / "test.yml"
        playbook.write_text(playbook_content)
        
        result = subprocess.run(
            [
                sys.executable, "-m", "sansible.san_cli",
                "run",
                "-i", str(ssh_inventory),
                str(playbook),
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        assert result.returncode == 0, f"Failed: {result.stdout}\n{result.stderr}"
    
    def test_ssh_file_operations(self, ssh_inventory: Path, ssh_playbook: Path):
        """Test full playbook with file operations."""
        result = subprocess.run(
            [
                sys.executable, "-m", "sansible.san_cli",
                "run",
                "-i", str(ssh_inventory),
                str(ssh_playbook),
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        assert result.returncode == 0, f"Failed: {result.stdout}\n{result.stderr}"
        
        import json
        data = json.loads(result.stdout)
        stats = data.get("stats", {}).get("sshtest", {})
        assert stats.get("failed", 1) == 0
        assert stats.get("unreachable", 1) == 0


@pytest.mark.skipif(not ASYNCSSH_AVAILABLE, reason=SKIP_ASYNCSSH)
class TestSSHConnectionUnit:
    """Unit tests for SSH connection that don't require Docker."""
    
    def test_ssh_connection_import(self):
        """SSH connection module should import correctly."""
        from sansible.connections.ssh_asyncssh import SSHConnection, HAS_ASYNCSSH
        assert HAS_ASYNCSSH is True
    
    def test_ssh_connection_requires_asyncssh(self):
        """SSHConnection should require asyncssh."""
        from sansible.connections.ssh_asyncssh import SSHConnection
        from sansible.engine.inventory import Host
        
        # Create a mock host with variables
        host = Host(name="test", variables={'ansible_host': 'localhost'})
        
        # Should be able to create connection (asyncssh is installed)
        conn = SSHConnection(host)
        assert conn is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
