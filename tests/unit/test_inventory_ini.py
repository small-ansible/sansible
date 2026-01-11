"""
Tests for INI inventory parsing.
"""

import pytest
import tempfile
from pathlib import Path

from sansible.engine.inventory import InventoryManager, Host


class TestINIInventoryParser:
    """Test INI inventory file parsing."""
    
    def test_parse_simple_host(self, tmp_path: Path):
        """Test parsing a simple host."""
        inventory_file = tmp_path / "inventory.ini"
        inventory_file.write_text("localhost\n")
        
        mgr = InventoryManager()
        mgr.parse(str(inventory_file))
        
        hosts = mgr.get_hosts("all")
        assert len(hosts) == 1
        assert hosts[0].name == "localhost"
    
    def test_parse_host_with_vars(self, tmp_path: Path):
        """Test parsing hosts with inline variables."""
        inventory_file = tmp_path / "inventory.ini"
        inventory_file.write_text(
            "web1 ansible_host=192.168.1.10 ansible_user=admin ansible_connection=ssh\n"
        )
        
        mgr = InventoryManager()
        mgr.parse(str(inventory_file))
        
        hosts = mgr.get_hosts("all")
        assert len(hosts) == 1
        assert hosts[0].name == "web1"
        assert hosts[0].ansible_host == "192.168.1.10"
        assert hosts[0].ansible_user == "admin"
        assert hosts[0].ansible_connection == "ssh"
    
    def test_parse_groups(self, tmp_path: Path):
        """Test parsing group sections."""
        inventory_file = tmp_path / "inventory.ini"
        inventory_file.write_text("""
[webservers]
web1
web2

[dbservers]
db1
db2
""")
        
        mgr = InventoryManager()
        mgr.parse(str(inventory_file))
        
        web_hosts = mgr.get_hosts("webservers")
        assert len(web_hosts) == 2
        assert {h.name for h in web_hosts} == {"web1", "web2"}
        
        db_hosts = mgr.get_hosts("dbservers")
        assert len(db_hosts) == 2
        assert {h.name for h in db_hosts} == {"db1", "db2"}
    
    def test_parse_group_children(self, tmp_path: Path):
        """Test parsing group children."""
        inventory_file = tmp_path / "inventory.ini"
        inventory_file.write_text("""
[webservers]
web1
web2

[dbservers]
db1

[all_servers:children]
webservers
dbservers
""")
        
        mgr = InventoryManager()
        mgr.parse(str(inventory_file))
        
        all_hosts = mgr.get_hosts("all_servers")
        assert len(all_hosts) == 3
        assert {h.name for h in all_hosts} == {"web1", "web2", "db1"}
    
    def test_parse_group_vars(self, tmp_path: Path):
        """Test parsing group variables."""
        inventory_file = tmp_path / "inventory.ini"
        inventory_file.write_text("""
[webservers]
web1

[webservers:vars]
http_port=80
app_env=production
""")
        
        mgr = InventoryManager()
        mgr.parse(str(inventory_file))
        
        # Group vars are stored on the group, use get_host_vars to get merged vars
        host_vars = mgr.get_host_vars("web1")
        # Values might be parsed as native types (int, bool, etc.)
        assert host_vars.get("http_port") == 80  # Parsed as int
        assert host_vars.get("app_env") == "production"
    
    def test_get_hosts_all(self, tmp_path: Path):
        """Test getting all hosts."""
        inventory_file = tmp_path / "inventory.ini"
        inventory_file.write_text("""
host1
host2

[group1]
host3
""")
        
        mgr = InventoryManager()
        mgr.parse(str(inventory_file))
        
        all_hosts = mgr.get_hosts("all")
        assert len(all_hosts) == 3
    
    def test_get_hosts_pattern(self, tmp_path: Path):
        """Test getting hosts by pattern."""
        inventory_file = tmp_path / "inventory.ini"
        inventory_file.write_text("""
[webservers]
web1
web2

[dbservers]
db1
""")
        
        mgr = InventoryManager()
        mgr.parse(str(inventory_file))
        
        # Single group
        hosts = mgr.get_hosts("webservers")
        assert {h.name for h in hosts} == {"web1", "web2"}
        
        # Single host
        hosts = mgr.get_hosts("web1")
        assert len(hosts) == 1
        assert hosts[0].name == "web1"
    
    def test_localhost_implicit(self, tmp_path: Path):
        """Test that localhost gets local connection when set explicitly."""
        inventory_file = tmp_path / "inventory.ini"
        inventory_file.write_text("localhost ansible_connection=local\n")
        
        mgr = InventoryManager()
        mgr.parse(str(inventory_file))
        
        hosts = mgr.get_hosts("localhost")
        assert len(hosts) == 1
        assert hosts[0].ansible_connection == "local"


class TestHostModel:
    """Test Host model."""
    
    def test_host_defaults(self):
        """Test Host default values."""
        host = Host(name="test")
        assert host.name == "test"
        # ansible_host defaults to name when not set in vars
        assert host.ansible_host == "test"
        assert host.ansible_user is None
        # ansible_connection defaults to 'ssh'
        assert host.ansible_connection == "ssh"
        assert host.vars == {}
    
    def test_host_ansible_host_property(self):
        """Test Host.ansible_host property."""
        host = Host(name="myhost")
        assert host.ansible_host == "myhost"
        
        host.vars["ansible_host"] = "192.168.1.1"
        assert host.ansible_host == "192.168.1.1"
    
    def test_host_get_variable(self):
        """Test Host.get_variable method."""
        host = Host(name="test", variables={"foo": "bar"})
        assert host.get_variable("foo") == "bar"
        assert host.get_variable("missing") is None
        assert host.get_variable("missing", "default") == "default"
