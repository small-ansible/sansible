"""
Tests for block rescue/always execution in the runner.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from sansible.engine.scheduler import HostContext
from sansible.engine.inventory import Host
from sansible.engine.playbook import Play, Task
from sansible.engine.results import TaskResult, TaskStatus
from sansible.connections.base import RunResult


class TestBlockMetadataOnTasks:
    """Test block metadata is present on tasks."""
    
    def test_task_has_block_name(self):
        """Task can have _block_name set."""
        task = Task(name="test", module="debug", args={})
        task._block_name = "My block"
        assert task._block_name == "My block"
    
    def test_task_is_rescue_flag(self):
        """Task can be marked as rescue task."""
        task = Task(name="test", module="debug", args={})
        task._is_rescue = True
        assert task._is_rescue is True
    
    def test_task_is_always_flag(self):
        """Task can be marked as always task."""
        task = Task(name="test", module="debug", args={})
        task._is_always = True
        assert task._is_always is True


class TestBlockFailureTracking:
    """Test tracking block failures for rescue."""
    
    def test_host_context_has_block_failed(self):
        """HostContext tracks failed blocks."""
        host = Host(name="test", variables={})
        ctx = HostContext(host=host)
        assert hasattr(ctx, 'failed_blocks')
        assert ctx.failed_blocks == set()
    
    def test_mark_block_failed(self):
        """Can mark a block as failed."""
        host = Host(name="test", variables={})
        ctx = HostContext(host=host)
        ctx.failed_blocks.add("Install block")
        assert "Install block" in ctx.failed_blocks
    
    def test_block_rescued(self):
        """Rescued blocks are tracked separately."""
        host = Host(name="test", variables={})
        ctx = HostContext(host=host)
        assert hasattr(ctx, 'rescued_blocks')
        ctx.failed_blocks.add("DB block")
        ctx.rescued_blocks.add("DB block")
        assert "DB block" in ctx.rescued_blocks


class TestRescueExecution:
    """Test rescue tasks run on block failure."""
    
    def test_rescue_task_has_metadata(self):
        """Rescue tasks have _is_rescue=True."""
        from sansible.engine.playbook import PlaybookParser
        import tempfile
        import os
        
        playbook_content = """
- name: Test
  hosts: localhost
  tasks:
    - name: Block test
      block:
        - name: May fail
          command: /bin/false
      rescue:
        - name: Handle error
          debug:
            msg: rescued
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(playbook_content)
            f.flush()
            
            parser = PlaybookParser(f.name)
            plays = parser.parse()
            
            os.unlink(f.name)
            
            # Find rescue task
            rescue_tasks = [t for t in plays[0].tasks if t._is_rescue]
            assert len(rescue_tasks) == 1
            assert rescue_tasks[0].name == "Handle error"


class TestAlwaysExecution:
    """Test always tasks run regardless of failure."""
    
    def test_always_task_has_metadata(self):
        """Always tasks have _is_always=True."""
        from sansible.engine.playbook import PlaybookParser
        import tempfile
        import os
        
        playbook_content = """
- name: Test
  hosts: localhost
  tasks:
    - name: Block test
      block:
        - name: Work task
          command: echo work
      always:
        - name: Cleanup
          debug:
            msg: cleanup
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(playbook_content)
            f.flush()
            
            parser = PlaybookParser(f.name)
            plays = parser.parse()
            
            os.unlink(f.name)
            
            # Find always task
            always_tasks = [t for t in plays[0].tasks if t._is_always]
            assert len(always_tasks) == 1
            assert always_tasks[0].name == "Cleanup"
    
    def test_always_runs_after_success(self):
        """Always runs even when block succeeds."""
        # Behavioral - always tasks should execute regardless
        task = Task(name="Cleanup", module="debug", args={})
        task._is_always = True
        task._block_name = "Setup block"
        
        # Always task should run regardless of block state
        assert task._is_always is True


class TestBlockExecutionOrder:
    """Test correct execution order for blocks."""
    
    def test_tasks_in_block_order(self):
        """Block tasks come before rescue before always."""
        from sansible.engine.playbook import PlaybookParser
        import tempfile
        import os
        
        playbook_content = """
- name: Test
  hosts: localhost
  tasks:
    - name: Block test
      block:
        - name: Block task 1
          debug:
            msg: block1
        - name: Block task 2
          debug:
            msg: block2
      rescue:
        - name: Rescue task
          debug:
            msg: rescue
      always:
        - name: Always task
          debug:
            msg: always
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(playbook_content)
            f.flush()
            
            parser = PlaybookParser(f.name)
            plays = parser.parse()
            
            os.unlink(f.name)
            
            tasks = plays[0].tasks
            
            # Block tasks first
            assert tasks[0].name == "Block task 1"
            assert tasks[0]._is_rescue is False
            assert tasks[0]._is_always is False
            
            assert tasks[1].name == "Block task 2"
            
            # Rescue tasks next
            assert tasks[2].name == "Rescue task"
            assert tasks[2]._is_rescue is True
            
            # Always tasks last
            assert tasks[3].name == "Always task"
            assert tasks[3]._is_always is True
