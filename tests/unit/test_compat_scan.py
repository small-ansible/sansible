"""
Tests for compatibility scanner.
"""

import json
import pytest
from pathlib import Path

from sansible.compat_scan import CompatibilityScanner, ScanResult, SUPPORTED_MODULES


class TestCompatibilityScanner:
    """Test compatibility scanner functionality."""
    
    def test_scanner_creation(self, tmp_path: Path):
        """Test scanner can be created."""
        scanner = CompatibilityScanner(str(tmp_path))
        assert scanner.repo_path == tmp_path
    
    def test_scan_empty_repo(self, tmp_path: Path):
        """Test scanning empty directory."""
        scanner = CompatibilityScanner(str(tmp_path))
        result = scanner.scan()
        
        assert result.files_scanned == 0
        assert result.playbooks_found == 0
        assert len(result.modules_used) == 0
    
    def test_scan_simple_playbook(self, tmp_path: Path):
        """Test scanning simple playbook."""
        playbook = tmp_path / "playbook.yml"
        playbook.write_text("""
---
- hosts: all
  tasks:
    - debug:
        msg: "Hello"
    - copy:
        src: /tmp/a
        dest: /tmp/b
    - command: whoami
""")
        
        scanner = CompatibilityScanner(str(tmp_path))
        result = scanner.scan()
        
        assert result.files_scanned == 1
        assert result.playbooks_found == 1
        assert "debug" in result.modules_used
        assert "copy" in result.modules_used
        assert "command" in result.modules_used
    
    def test_scan_detects_unsupported_modules(self, tmp_path: Path):
        """Test scanner detects unsupported modules."""
        playbook = tmp_path / "playbook.yml"
        playbook.write_text("""
---
- hosts: all
  tasks:
    - apt:
        name: nginx
    - yum:
        name: httpd
    - service:
        name: nginx
        state: started
""")
        
        scanner = CompatibilityScanner(str(tmp_path))
        result = scanner.scan()
        
        data = result.to_dict()
        unsupported = data["modules"]["unsupported"]
        
        assert "apt" in unsupported
        assert "yum" in unsupported
        assert "service" in unsupported
    
    def test_scan_detects_features(self, tmp_path: Path):
        """Test scanner detects feature usage."""
        playbook = tmp_path / "playbook.yml"
        playbook.write_text("""
---
- hosts: all
  gather_facts: true
  become: true
  vars:
    myvar: value
  tasks:
    - debug:
        msg: "{{ myvar }}"
      when: some_condition
      register: result
      tags:
        - always
""")
        
        scanner = CompatibilityScanner(str(tmp_path))
        result = scanner.scan()
        
        assert "gather_facts" in result.features_used
        assert "become" in result.features_used
        assert "vars" in result.features_used
        assert "when" in result.features_used
        assert "register" in result.features_used
        assert "tags" in result.features_used
    
    def test_scan_roles_directory(self, tmp_path: Path):
        """Test scanner counts roles."""
        # Create roles
        (tmp_path / "roles" / "role1" / "tasks").mkdir(parents=True)
        (tmp_path / "roles" / "role2" / "tasks").mkdir(parents=True)
        (tmp_path / "roles" / "role3" / "tasks").mkdir(parents=True)
        
        # Create tasks files
        for role in ["role1", "role2", "role3"]:
            (tmp_path / "roles" / role / "tasks" / "main.yml").write_text("""
---
- debug:
    msg: "Role task"
""")
        
        scanner = CompatibilityScanner(str(tmp_path))
        result = scanner.scan()
        
        assert result.roles_found == 3
    
    def test_scan_detects_connection_types(self, tmp_path: Path):
        """Test scanner detects connection types."""
        inventory = tmp_path / "inventory.yml"
        inventory.write_text("""
---
all:
  hosts:
    linux1:
      ansible_connection: ssh
    win1:
      ansible_connection: winrm
""")
        
        scanner = CompatibilityScanner(str(tmp_path))
        result = scanner.scan()
        
        assert "ssh" in result.connections_used
        assert "winrm" in result.connections_used
    
    def test_scan_extracts_variables(self, tmp_path: Path):
        """Test scanner extracts variable names."""
        playbook = tmp_path / "playbook.yml"
        playbook.write_text("""
---
- hosts: all
  tasks:
    - debug:
        msg: "{{ my_var }} and {{ another_var }}"
""")
        
        scanner = CompatibilityScanner(str(tmp_path))
        result = scanner.scan()
        
        assert "my_var" in result.vars_used
        assert "another_var" in result.vars_used


class TestScanResult:
    """Test ScanResult output."""
    
    def test_to_dict(self, tmp_path: Path):
        """Test ScanResult.to_dict()."""
        result = ScanResult(repo_path=str(tmp_path))
        result.files_scanned = 5
        result.playbooks_found = 2
        result.modules_used["debug"] = 10
        result.modules_used["copy"] = 5
        
        data = result.to_dict()
        
        assert data["summary"]["files_scanned"] == 5
        assert data["summary"]["playbooks_found"] == 2
        assert data["modules"]["usage_count"]["debug"] == 10
    
    def test_to_markdown(self, tmp_path: Path):
        """Test ScanResult.to_markdown()."""
        result = ScanResult(repo_path=str(tmp_path))
        result.files_scanned = 5
        result.playbooks_found = 2
        result.modules_used["debug"] = 10
        result.modules_used["apt"] = 5  # Unsupported
        
        md = result.to_markdown()
        
        assert "# Sansible Compatibility Scan" in md
        assert "debug" in md
        assert "Supported" in md
        assert "Unsupported" in md


class TestSupportedModulesConstant:
    """Test SUPPORTED_MODULES constant."""
    
    def test_core_modules_in_constant(self):
        """Test core modules are in SUPPORTED_MODULES."""
        expected = {"copy", "command", "shell", "debug", "set_fact", "file", "template"}
        assert expected.issubset(SUPPORTED_MODULES)
    
    def test_windows_modules_in_constant(self):
        """Test Windows modules are in SUPPORTED_MODULES."""
        expected = {"win_copy", "win_command", "win_shell", "win_file"}
        assert expected.issubset(SUPPORTED_MODULES)
