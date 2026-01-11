"""
Unit tests for include_tasks, import_tasks, and import_role features.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import os

from sansible.engine.playbook import PlaybookParser, Task


class TestIncludeTasks:
    """Tests for include_tasks and import_tasks."""
    
    def test_include_tasks_loads_external_file(self, tmp_path: Path):
        """include_tasks should load tasks from external file."""
        # Create included tasks file
        tasks_file = tmp_path / "tasks" / "included.yml"
        tasks_file.parent.mkdir(parents=True)
        tasks_file.write_text("""
- name: Included task 1
  debug:
    msg: "From included file"

- name: Included task 2
  command: echo hello
""")
        
        # Create main playbook
        playbook = tmp_path / "playbook.yml"
        playbook.write_text(f"""
- name: Test play
  hosts: localhost
  tasks:
    - name: First task
      debug:
        msg: "First"
    
    - include_tasks: tasks/included.yml
    
    - name: Last task
      debug:
        msg: "Last"
""")
        
        parser = PlaybookParser(playbook)
        plays = parser.parse()
        
        assert len(plays) == 1
        assert len(plays[0].tasks) == 4  # First + 2 included + Last
        assert plays[0].tasks[0].name == "First task"
        assert plays[0].tasks[1].name == "Included task 1"
        assert plays[0].tasks[2].name == "Included task 2"
        assert plays[0].tasks[3].name == "Last task"
    
    def test_import_tasks_loads_external_file(self, tmp_path: Path):
        """import_tasks should load tasks from external file."""
        # Create imported tasks file
        tasks_file = tmp_path / "tasks" / "imported.yml"
        tasks_file.parent.mkdir(parents=True)
        tasks_file.write_text("""
- name: Imported task
  debug:
    msg: "Imported"
""")
        
        # Create main playbook
        playbook = tmp_path / "playbook.yml"
        playbook.write_text(f"""
- name: Test play
  hosts: localhost
  tasks:
    - import_tasks: tasks/imported.yml
""")
        
        parser = PlaybookParser(playbook)
        plays = parser.parse()
        
        assert len(plays) == 1
        assert len(plays[0].tasks) == 1
        assert plays[0].tasks[0].name == "Imported task"
    
    def test_include_tasks_with_when(self, tmp_path: Path):
        """include_tasks with when applies condition to included tasks."""
        tasks_file = tmp_path / "conditional.yml"
        tasks_file.write_text("""
- name: Conditional task
  debug:
    msg: "Conditional"
""")
        
        playbook = tmp_path / "playbook.yml"
        playbook.write_text(f"""
- name: Test play
  hosts: localhost
  tasks:
    - include_tasks: conditional.yml
      when: some_var is defined
""")
        
        parser = PlaybookParser(playbook)
        plays = parser.parse()
        
        assert len(plays[0].tasks) == 1
        assert plays[0].tasks[0].when == "some_var is defined"
    
    def test_include_tasks_with_tags(self, tmp_path: Path):
        """include_tasks with tags applies tags to included tasks."""
        tasks_file = tmp_path / "tagged.yml"
        tasks_file.write_text("""
- name: Tagged task
  debug:
    msg: "Tagged"
""")
        
        playbook = tmp_path / "playbook.yml"
        playbook.write_text(f"""
- name: Test play
  hosts: localhost
  tasks:
    - include_tasks: tagged.yml
      tags:
        - setup
        - config
""")
        
        parser = PlaybookParser(playbook)
        plays = parser.parse()
        
        assert len(plays[0].tasks) == 1
        assert "setup" in plays[0].tasks[0].tags
        assert "config" in plays[0].tasks[0].tags


class TestImportRole:
    """Tests for include_role and import_role."""
    
    def test_import_role_loads_role_tasks(self, tmp_path: Path):
        """import_role should load tasks from a role."""
        # Create role structure
        role_dir = tmp_path / "roles" / "myrole"
        (role_dir / "tasks").mkdir(parents=True)
        (role_dir / "tasks" / "main.yml").write_text("""
- name: Role task 1
  debug:
    msg: "From role"
- name: Role task 2
  command: echo role
""")
        
        # Create playbook
        playbook = tmp_path / "playbook.yml"
        playbook.write_text("""
- name: Test play
  hosts: localhost
  tasks:
    - import_role:
        name: myrole
""")
        
        parser = PlaybookParser(playbook)
        plays = parser.parse()
        
        assert len(plays) == 1
        assert len(plays[0].tasks) == 2
        assert plays[0].tasks[0].name == "Role task 1"
        assert plays[0].tasks[1].name == "Role task 2"
    
    def test_include_role_with_when(self, tmp_path: Path):
        """include_role with when applies condition to role tasks."""
        # Create role
        role_dir = tmp_path / "roles" / "conditional_role"
        (role_dir / "tasks").mkdir(parents=True)
        (role_dir / "tasks" / "main.yml").write_text("""
- name: Conditional role task
  debug:
    msg: "Conditional"
""")
        
        playbook = tmp_path / "playbook.yml"
        playbook.write_text("""
- name: Test play
  hosts: localhost
  tasks:
    - include_role:
        name: conditional_role
      when: condition_met
""")
        
        parser = PlaybookParser(playbook)
        plays = parser.parse()
        
        assert len(plays[0].tasks) == 1
        assert plays[0].tasks[0].when == "condition_met"
    
    def test_import_role_string_format(self, tmp_path: Path):
        """import_role with string format should work."""
        role_dir = tmp_path / "roles" / "simple_role"
        (role_dir / "tasks").mkdir(parents=True)
        (role_dir / "tasks" / "main.yml").write_text("""
- name: Simple role task
  debug:
    msg: "Simple"
""")
        
        playbook = tmp_path / "playbook.yml"
        playbook.write_text("""
- name: Test play
  hosts: localhost
  tasks:
    - import_role: simple_role
""")
        
        parser = PlaybookParser(playbook)
        plays = parser.parse()
        
        assert len(plays[0].tasks) == 1
        assert plays[0].tasks[0].name == "Simple role task"


class TestDelegateTo:
    """Tests for delegate_to feature."""
    
    def test_task_has_delegate_to_field(self):
        """Task should have delegate_to field."""
        task = Task(
            name="Test task",
            module="debug",
            args={"msg": "test"},
            delegate_to="localhost"
        )
        assert task.delegate_to == "localhost"
    
    def test_delegate_to_parsed_from_yaml(self, tmp_path: Path):
        """delegate_to should be parsed from YAML."""
        playbook = tmp_path / "playbook.yml"
        playbook.write_text("""
- name: Test play
  hosts: webservers
  tasks:
    - name: Run on localhost
      command: echo hello
      delegate_to: localhost
""")
        
        parser = PlaybookParser(playbook)
        plays = parser.parse()
        
        assert len(plays[0].tasks) == 1
        assert plays[0].tasks[0].delegate_to == "localhost"
    
    def test_delegate_to_default_none(self, tmp_path: Path):
        """delegate_to should default to None."""
        playbook = tmp_path / "playbook.yml"
        playbook.write_text("""
- name: Test play
  hosts: localhost
  tasks:
    - name: Normal task
      debug:
        msg: "No delegation"
""")
        
        parser = PlaybookParser(playbook)
        plays = parser.parse()
        
        assert plays[0].tasks[0].delegate_to is None
