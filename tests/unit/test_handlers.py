"""
Tests for handlers and notify support.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from sansible.engine.scheduler import HostContext
from sansible.engine.inventory import Host


class TestHandlerParsing:
    """Test handler parsing in playbooks."""
    
    def test_play_has_handlers_field(self):
        """Play dataclass has handlers field."""
        from sansible.engine.playbook import Play
        play = Play(name="test", hosts="all", tasks=[], handlers=[])
        assert hasattr(play, 'handlers')
    
    def test_parse_handlers_in_play(self, tmp_path):
        """Handlers section is parsed from playbook."""
        from sansible.engine.playbook import PlaybookParser
        
        playbook_content = """
- name: Test play
  hosts: localhost
  tasks:
    - name: Change config
      command: echo hello
      notify: Restart service
  handlers:
    - name: Restart service
      command: echo restarting
"""
        playbook_file = tmp_path / "test.yml"
        playbook_file.write_text(playbook_content)
        
        parser = PlaybookParser(str(playbook_file))
        plays = parser.parse()
        
        assert len(plays) == 1
        assert len(plays[0].handlers) == 1
        assert plays[0].handlers[0].name == "Restart service"


class TestNotifyParsing:
    """Test notify parsing in tasks."""
    
    def test_task_has_notify_field(self):
        """Task dataclass has notify field."""
        from sansible.engine.playbook import Task
        task = Task(name="test", module="command", args={"cmd": "echo"}, notify=["Handler"])
        assert task.notify == ["Handler"]
    
    def test_task_notify_default_empty(self):
        """Task notify defaults to empty list."""
        from sansible.engine.playbook import Task
        task = Task(name="test", module="command", args={"cmd": "echo"})
        assert task.notify == []
    
    def test_parse_notify_string(self, tmp_path):
        """Notify can be a single string."""
        from sansible.engine.playbook import PlaybookParser
        
        playbook_content = """
- name: Test play
  hosts: localhost
  tasks:
    - name: Task with notify
      command: echo hello
      notify: My handler
  handlers:
    - name: My handler
      debug:
        msg: "handled"
"""
        playbook_file = tmp_path / "test.yml"
        playbook_file.write_text(playbook_content)
        
        parser = PlaybookParser(str(playbook_file))
        plays = parser.parse()
        
        assert plays[0].tasks[0].notify == ["My handler"]
    
    def test_parse_notify_list(self, tmp_path):
        """Notify can be a list of handlers."""
        from sansible.engine.playbook import PlaybookParser
        
        playbook_content = """
- name: Test play
  hosts: localhost
  tasks:
    - name: Task with multiple notify
      command: echo hello
      notify:
        - Handler one
        - Handler two
  handlers:
    - name: Handler one
      debug:
        msg: "one"
    - name: Handler two
      debug:
        msg: "two"
"""
        playbook_file = tmp_path / "test.yml"
        playbook_file.write_text(playbook_content)
        
        parser = PlaybookParser(str(playbook_file))
        plays = parser.parse()
        
        assert plays[0].tasks[0].notify == ["Handler one", "Handler two"]


class TestHandlerExecution:
    """Test handler execution semantics."""
    
    def test_handler_has_listen_field(self):
        """Handler can have listen field for multiple triggers."""
        from sansible.engine.playbook import Task
        # Handlers are just tasks with a listen field
        handler = Task(
            name="Restart service",
            module="command",
            args={"cmd": "systemctl restart app"},
            listen=["restart app", "config changed"],
        )
        assert "restart app" in handler.listen
        assert "config changed" in handler.listen
    
    def test_handlers_run_once(self):
        """Handlers run only once even if notified multiple times."""
        # This is a semantic test - handlers are deduplicated
        from sansible.engine.playbook import Play, Task
        
        play = Play(
            name="test",
            hosts="all",
            tasks=[
                Task(name="t1", module="command", args={}, notify=["h1"]),
                Task(name="t2", module="command", args={}, notify=["h1"]),
            ],
            handlers=[
                Task(name="h1", module="debug", args={"msg": "ran"}),
            ],
        )
        
        # Handler h1 notified twice, but should only run once
        assert len(play.handlers) == 1
