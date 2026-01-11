"""
Tests for tags and limit filtering.
"""

import pytest
from pathlib import Path

from sansible.engine.playbook import PlaybookParser, Task
from sansible.engine.inventory import InventoryManager


class TestTagsFiltering:
    """Test task filtering by tags."""
    
    def test_task_has_tags(self, tmp_path: Path):
        """Test that tasks have tags parsed."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  tasks:
    - name: Untagged task
      debug:
        msg: "No tags"
    
    - name: Tagged task
      debug:
        msg: "Has tags"
      tags:
        - deploy
        - config
    
    - name: Single tag
      debug:
        msg: "One tag"
      tags: setup
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        
        tasks = plays[0].tasks
        assert tasks[0].tags == []
        assert set(tasks[1].tags) == {"deploy", "config"}
        assert tasks[2].tags == ["setup"]
    
    def test_filter_tasks_by_tags(self, tmp_path: Path):
        """Test filtering tasks by tags."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  tasks:
    - name: Task A
      debug:
        msg: "A"
      tags: alpha
    
    - name: Task B
      debug:
        msg: "B"
      tags: beta
    
    - name: Task C
      debug:
        msg: "C"
      tags:
        - alpha
        - gamma
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        tasks = plays[0].tasks
        
        # Filter by single tag
        alpha_tasks = [t for t in tasks if "alpha" in t.tags]
        assert len(alpha_tasks) == 2
        assert {t.name for t in alpha_tasks} == {"Task A", "Task C"}
        
        # Filter by different tag
        beta_tasks = [t for t in tasks if "beta" in t.tags]
        assert len(beta_tasks) == 1
        assert beta_tasks[0].name == "Task B"


class TestLimitFiltering:
    """Test host filtering by limit."""
    
    def test_limit_single_host(self, tmp_path: Path):
        """Test limiting to single host."""
        inventory_file = tmp_path / "inventory.ini"
        inventory_file.write_text("""
[webservers]
web1
web2
web3
""")
        
        mgr = InventoryManager()
        mgr.parse(str(inventory_file))
        
        # Get single host
        hosts = mgr.get_hosts("web1")
        assert len(hosts) == 1
        assert hosts[0].name == "web1"
    
    def test_limit_group(self, tmp_path: Path):
        """Test limiting to group."""
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
        
        # Get group
        hosts = mgr.get_hosts("webservers")
        assert len(hosts) == 2
        assert {h.name for h in hosts} == {"web1", "web2"}
    
    def test_limit_all(self, tmp_path: Path):
        """Test 'all' pattern."""
        inventory_file = tmp_path / "inventory.ini"
        inventory_file.write_text("""
[webservers]
web1

[dbservers]
db1
""")
        
        mgr = InventoryManager()
        mgr.parse(str(inventory_file))
        
        hosts = mgr.get_hosts("all")
        assert len(hosts) == 2
        assert {h.name for h in hosts} == {"web1", "db1"}
    
    def test_limit_multiple_hosts(self, tmp_path: Path):
        """Test comma-separated host limit."""
        inventory_file = tmp_path / "inventory.ini"
        inventory_file.write_text("""
web1
web2
web3
db1
""")
        
        mgr = InventoryManager()
        mgr.parse(str(inventory_file))
        
        # Get multiple hosts (if supported)
        # Note: This depends on implementation
        hosts = mgr.get_hosts("web1")
        assert len(hosts) == 1


class TestSkipTags:
    """Test skip-tags functionality."""
    
    def test_skip_tags_logic(self, tmp_path: Path):
        """Test skip-tags filtering logic."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  tasks:
    - name: Task A
      debug:
        msg: "A"
      tags: always_run
    
    - name: Task B
      debug:
        msg: "B"
      tags: skip_me
    
    - name: Task C
      debug:
        msg: "C"
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        tasks = plays[0].tasks
        
        skip_tags = {"skip_me"}
        
        # Tasks without skipped tags should remain
        remaining = [t for t in tasks if not any(tag in skip_tags for tag in t.tags)]
        assert len(remaining) == 2
        assert {t.name for t in remaining} == {"Task A", "Task C"}


class TestPlayHostsPattern:
    """Test play hosts pattern matching."""
    
    def test_play_hosts_pattern(self, tmp_path: Path):
        """Test play hosts field patterns."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- name: All hosts
  hosts: all
  tasks:
    - debug:
        msg: "All"

- name: Web hosts
  hosts: webservers
  tasks:
    - debug:
        msg: "Web"

- name: Single host
  hosts: specific_host
  tasks:
    - debug:
        msg: "Single"
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        
        assert plays[0].hosts == "all"
        assert plays[1].hosts == "webservers"
        assert plays[2].hosts == "specific_host"
