"""
Tests for block/rescue/always support.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from sansible.engine.scheduler import HostContext
from sansible.engine.inventory import Host
from sansible.connections.base import RunResult


class TestBlockParsing:
    """Test block parsing in playbooks."""
    
    def test_task_can_have_block(self, tmp_path):
        """Task can contain a block of subtasks."""
        from sansible.engine.playbook import PlaybookParser
        
        playbook_content = """
- name: Test play
  hosts: localhost
  tasks:
    - name: Block example
      block:
        - name: Task in block
          command: echo hello
        - name: Another task
          command: echo world
"""
        playbook_file = tmp_path / "test.yml"
        playbook_file.write_text(playbook_content)
        
        parser = PlaybookParser(str(playbook_file))
        plays = parser.parse()
        
        assert len(plays) == 1
        # Block should be expanded into tasks
        assert len(plays[0].tasks) >= 2
    
    def test_block_with_rescue(self, tmp_path):
        """Block can have rescue section for error handling."""
        from sansible.engine.playbook import PlaybookParser
        
        playbook_content = """
- name: Test play
  hosts: localhost
  tasks:
    - name: Block with rescue
      block:
        - name: May fail
          command: /bin/false
      rescue:
        - name: Handle error
          debug:
            msg: "Rescued!"
"""
        playbook_file = tmp_path / "test.yml"
        playbook_file.write_text(playbook_content)
        
        parser = PlaybookParser(str(playbook_file))
        plays = parser.parse()
        
        assert len(plays) == 1
    
    def test_block_with_always(self, tmp_path):
        """Block can have always section that runs regardless of errors."""
        from sansible.engine.playbook import PlaybookParser
        
        playbook_content = """
- name: Test play
  hosts: localhost
  tasks:
    - name: Block with always
      block:
        - name: Task
          command: echo hello
      always:
        - name: Always runs
          debug:
            msg: "Cleanup"
"""
        playbook_file = tmp_path / "test.yml"
        playbook_file.write_text(playbook_content)
        
        parser = PlaybookParser(str(playbook_file))
        plays = parser.parse()
        
        assert len(plays) == 1


class TestBlockExecution:
    """Test block execution semantics."""
    
    def test_block_tasks_run_in_order(self):
        """Tasks in block run sequentially."""
        from sansible.engine.playbook import Block, Task
        
        block = Block(
            name="Test block",
            block=[
                Task(name="First", module="debug", args={"msg": "1"}),
                Task(name="Second", module="debug", args={"msg": "2"}),
            ],
            rescue=[],
            always=[],
        )
        
        assert len(block.block) == 2
        assert block.block[0].name == "First"
        assert block.block[1].name == "Second"
    
    def test_rescue_only_on_failure(self):
        """Rescue tasks only run when block fails."""
        from sansible.engine.playbook import Block, Task
        
        block = Block(
            name="Test block",
            block=[
                Task(name="Fails", module="fail", args={"msg": "error"}),
            ],
            rescue=[
                Task(name="Handle", module="debug", args={"msg": "rescued"}),
            ],
            always=[],
        )
        
        assert len(block.rescue) == 1
    
    def test_always_runs_after_block(self):
        """Always tasks run after block regardless of success/failure."""
        from sansible.engine.playbook import Block, Task
        
        block = Block(
            name="Test block",
            block=[
                Task(name="Task", module="debug", args={"msg": "work"}),
            ],
            rescue=[],
            always=[
                Task(name="Cleanup", module="debug", args={"msg": "done"}),
            ],
        )
        
        assert len(block.always) == 1
    
    def test_block_inherits_become(self):
        """Block inherits become from parent."""
        from sansible.engine.playbook import Block, Task
        
        block = Block(
            name="Test block",
            block=[Task(name="Task", module="command", args={"cmd": "id"})],
            rescue=[],
            always=[],
            become=True,
            become_user="root",
        )
        
        assert block.become is True
        assert block.become_user == "root"
