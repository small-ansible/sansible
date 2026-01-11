"""
Tests for playbook parsing and role expansion.
"""

import pytest
from pathlib import Path

from sansible.engine.playbook import PlaybookParser, Play, Task, SUPPORTED_MODULES
from sansible.engine.errors import ParseError, UnsupportedFeatureError


class TestPlaybookParser:
    """Test playbook parsing."""
    
    def test_parse_simple_playbook(self, tmp_path: Path):
        """Test parsing a simple playbook."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- name: Test Play
  hosts: all
  tasks:
    - name: Debug task
      debug:
        msg: "Hello World"
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        
        assert len(plays) == 1
        assert plays[0].name == "Test Play"
        assert plays[0].hosts == "all"
        assert len(plays[0].tasks) == 1
        assert plays[0].tasks[0].name == "Debug task"
        assert plays[0].tasks[0].module == "debug"
    
    def test_parse_multiple_plays(self, tmp_path: Path):
        """Test parsing multiple plays."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- name: Play 1
  hosts: webservers
  tasks:
    - debug:
        msg: "Play 1"

- name: Play 2
  hosts: dbservers
  tasks:
    - debug:
        msg: "Play 2"
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        
        assert len(plays) == 2
        assert plays[0].name == "Play 1"
        assert plays[1].name == "Play 2"
    
    def test_parse_task_with_register(self, tmp_path: Path):
        """Test parsing task with register."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  tasks:
    - command: whoami
      register: result
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        
        assert plays[0].tasks[0].register == "result"
    
    def test_parse_task_with_when(self, tmp_path: Path):
        """Test parsing task with when condition."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  tasks:
    - debug:
        msg: "Conditional"
      when: some_var == 'value'
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        
        assert plays[0].tasks[0].when == "some_var == 'value'"
    
    def test_parse_task_with_loop(self, tmp_path: Path):
        """Test parsing task with loop."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  tasks:
    - debug:
        msg: "Item {{ item }}"
      loop:
        - one
        - two
        - three
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        
        assert plays[0].tasks[0].loop == ["one", "two", "three"]
    
    def test_parse_play_vars(self, tmp_path: Path):
        """Test parsing play variables."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  vars:
    app_name: myapp
    version: "1.0.0"
  tasks:
    - debug:
        msg: "{{ app_name }}"
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        
        assert plays[0].vars["app_name"] == "myapp"
        assert plays[0].vars["version"] == "1.0.0"
    
    def test_parse_fqcn_modules(self, tmp_path: Path):
        """Test parsing FQCN module names."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  tasks:
    - name: Copy file
      ansible.builtin.copy:
        src: /tmp/a
        dest: /tmp/b
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        
        # FQCN should be normalized to short name
        assert plays[0].tasks[0].module == "copy"
    
    def test_parse_inline_args(self, tmp_path: Path):
        """Test parsing inline module arguments."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  tasks:
    - shell: echo "hello world"
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        
        assert plays[0].tasks[0].module == "shell"
        assert plays[0].tasks[0].args.get("_raw_params") == 'echo "hello world"'
    
    def test_error_missing_hosts(self, tmp_path: Path):
        """Test error on missing hosts field."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- name: Bad Play
  tasks:
    - debug:
        msg: "No hosts!"
""")
        
        parser = PlaybookParser(playbook_file)
        with pytest.raises(ParseError):
            parser.parse()
    
    def test_error_unsupported_module(self, tmp_path: Path):
        """Test error on unsupported module."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  tasks:
    - lineinfile:
        path: /etc/hosts
        line: "127.0.0.1 test"
""")
        
        parser = PlaybookParser(playbook_file)
        with pytest.raises(UnsupportedFeatureError):
            parser.parse()


class TestRoleExpansion:
    """Test role loading and expansion."""
    
    def test_parse_role_basic(self, tmp_path: Path):
        """Test parsing playbook with roles."""
        # Create role structure
        role_dir = tmp_path / "roles" / "myrole" / "tasks"
        role_dir.mkdir(parents=True)
        (role_dir / "main.yml").write_text("""
---
- name: Task from role
  debug:
    msg: "Hello from role"
""")
        
        # Create playbook
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  roles:
    - myrole
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        
        assert len(plays) == 1
        assert len(plays[0].tasks) == 1
        assert plays[0].tasks[0].name == "Task from role"
    
    def test_parse_role_with_vars(self, tmp_path: Path):
        """Test role with passed variables."""
        # Create role structure
        role_dir = tmp_path / "roles" / "myrole"
        tasks_dir = role_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "main.yml").write_text("""
---
- name: Show var
  debug:
    msg: "{{ role_var }}"
""")
        
        # Create role defaults
        defaults_dir = role_dir / "defaults"
        defaults_dir.mkdir(parents=True)
        (defaults_dir / "main.yml").write_text("""
---
role_var: default_value
""")
        
        # Create playbook
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  roles:
    - role: myrole
      role_var: custom_value
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        
        assert len(plays[0].tasks) == 1
        # Role vars should be stored on task
        assert hasattr(plays[0].tasks[0], '_role_vars')
    
    def test_parse_pre_and_post_tasks(self, tmp_path: Path):
        """Test pre_tasks and post_tasks ordering."""
        # Create role
        role_dir = tmp_path / "roles" / "myrole" / "tasks"
        role_dir.mkdir(parents=True)
        (role_dir / "main.yml").write_text("""
---
- name: Role task
  debug:
    msg: "Role"
""")
        
        # Create playbook
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  pre_tasks:
    - name: Pre task
      debug:
        msg: "Pre"
  roles:
    - myrole
  tasks:
    - name: Regular task
      debug:
        msg: "Regular"
  post_tasks:
    - name: Post task
      debug:
        msg: "Post"
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        
        # Order should be: pre_tasks, roles, tasks, post_tasks
        task_names = [t.name for t in plays[0].tasks]
        assert task_names == ["Pre task", "Role task", "Regular task", "Post task"]
    
    def test_role_not_found_error(self, tmp_path: Path):
        """Test error when role not found."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  roles:
    - nonexistent_role
""")
        
        parser = PlaybookParser(playbook_file)
        with pytest.raises(ParseError) as exc_info:
            parser.parse()
        assert "not found" in str(exc_info.value).lower()


class TestTaskParsing:
    """Test individual task parsing."""
    
    def test_parse_tags(self, tmp_path: Path):
        """Test parsing task tags."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  tasks:
    - debug:
        msg: "Tagged"
      tags:
        - deploy
        - config
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        
        assert set(plays[0].tasks[0].tags) == {"deploy", "config"}
    
    def test_parse_ignore_errors(self, tmp_path: Path):
        """Test parsing ignore_errors."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  tasks:
    - command: /bin/false
      ignore_errors: true
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        
        assert plays[0].tasks[0].ignore_errors is True
    
    def test_parse_changed_when(self, tmp_path: Path):
        """Test parsing changed_when."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text("""
---
- hosts: all
  tasks:
    - command: whoami
      register: result
      changed_when: result.rc != 0
""")
        
        parser = PlaybookParser(playbook_file)
        plays = parser.parse()
        
        assert plays[0].tasks[0].changed_when == "result.rc != 0"


class TestSupportedModules:
    """Test that expected modules are supported."""
    
    def test_core_modules_supported(self):
        """Test that core modules are in supported list."""
        core_modules = {'copy', 'command', 'shell', 'debug', 'set_fact', 'fail'}
        assert core_modules.issubset(SUPPORTED_MODULES)
    
    def test_windows_modules_supported(self):
        """Test that Windows modules are in supported list."""
        win_modules = {'win_copy', 'win_command', 'win_shell', 'win_file'}
        assert win_modules.issubset(SUPPORTED_MODULES)
    
    def test_new_modules_supported(self):
        """Test that newly added modules are supported."""
        new_modules = {'file', 'template'}
        assert new_modules.issubset(SUPPORTED_MODULES)
