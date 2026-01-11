"""
Unit tests for dynamic inventory support.
"""

import json
import os
import pytest
import stat
import sys
import tempfile
from pathlib import Path

from sansible.engine.inventory import InventoryManager

# Skip dynamic inventory tests on Windows - executable bit model doesn't work
pytestmark = pytest.mark.skipif(
    sys.platform == 'win32',
    reason="Dynamic inventory via execute bit not supported on Windows"
)


class TestDynamicInventory:
    """Tests for dynamic inventory scripts."""
    
    def test_executable_script_is_detected(self, tmp_path: Path):
        """Executable scripts should be detected and run."""
        # Create a simple dynamic inventory script
        script = tmp_path / "inventory.py"
        script.write_text('''#!/usr/bin/env python3
import json
import sys

if len(sys.argv) > 1 and sys.argv[1] == '--list':
    inventory = {
        "webservers": {
            "hosts": ["web1.example.com", "web2.example.com"],
            "vars": {"http_port": 80}
        },
        "dbservers": {
            "hosts": ["db1.example.com"]
        },
        "_meta": {
            "hostvars": {
                "web1.example.com": {"ansible_user": "admin"},
                "web2.example.com": {"ansible_user": "admin"},
                "db1.example.com": {"ansible_user": "dba"}
            }
        }
    }
    print(json.dumps(inventory))
''')
        # Make it executable
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        
        manager = InventoryManager()
        manager.parse(script)
        
        # Check hosts were loaded
        assert "web1.example.com" in manager.hosts
        assert "web2.example.com" in manager.hosts
        assert "db1.example.com" in manager.hosts
        
        # Check groups
        assert "webservers" in manager.groups
        assert "dbservers" in manager.groups
        
        # Check group vars
        assert manager.groups["webservers"].vars.get("http_port") == 80
        
        # Check host vars from _meta
        assert manager.hosts["web1.example.com"].vars.get("ansible_user") == "admin"
        assert manager.hosts["db1.example.com"].vars.get("ansible_user") == "dba"
    
    def test_simplified_format(self, tmp_path: Path):
        """Simplified format (group: [hosts]) should work."""
        script = tmp_path / "simple_inventory.py"
        script.write_text('''#!/usr/bin/env python3
import json
import sys

if len(sys.argv) > 1 and sys.argv[1] == '--list':
    inventory = {
        "webservers": ["host1", "host2", "host3"],
        "dbservers": ["db1", "db2"]
    }
    print(json.dumps(inventory))
''')
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        
        manager = InventoryManager()
        manager.parse(script)
        
        assert len(manager.hosts) == 5
        assert "host1" in manager.hosts
        assert "db1" in manager.hosts
    
    def test_children_groups(self, tmp_path: Path):
        """Children groups should be parsed correctly."""
        script = tmp_path / "children_inventory.py"
        script.write_text('''#!/usr/bin/env python3
import json
import sys

if len(sys.argv) > 1 and sys.argv[1] == '--list':
    inventory = {
        "all": {
            "children": ["webservers", "dbservers"]
        },
        "webservers": {
            "hosts": ["web1"]
        },
        "dbservers": {
            "hosts": ["db1"]
        }
    }
    print(json.dumps(inventory))
''')
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        
        manager = InventoryManager()
        manager.parse(script)
        
        assert "webservers" in manager.groups["all"].children
        assert "dbservers" in manager.groups["all"].children
    
    def test_non_executable_file_parsed_normally(self, tmp_path: Path):
        """Non-executable files should be parsed as INI/YAML."""
        inventory_file = tmp_path / "inventory.ini"
        inventory_file.write_text("""
[webservers]
web1
web2

[dbservers]
db1
""")
        
        manager = InventoryManager()
        manager.parse(inventory_file)
        
        assert "web1" in manager.hosts
        assert "db1" in manager.hosts
    
    def test_script_failure_raises_error(self, tmp_path: Path):
        """Script failures should raise InventoryError."""
        from sansible.engine.errors import InventoryError
        
        script = tmp_path / "failing_inventory.py"
        script.write_text('''#!/usr/bin/env python3
import sys
sys.exit(1)
''')
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        
        manager = InventoryManager()
        with pytest.raises(InventoryError, match="Dynamic inventory script failed"):
            manager.parse(script)
    
    def test_invalid_json_raises_error(self, tmp_path: Path):
        """Invalid JSON output should raise InventoryError."""
        from sansible.engine.errors import InventoryError
        
        script = tmp_path / "bad_json_inventory.py"
        script.write_text('''#!/usr/bin/env python3
print("not valid json")
''')
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        
        manager = InventoryManager()
        with pytest.raises(InventoryError, match="invalid JSON"):
            manager.parse(script)
