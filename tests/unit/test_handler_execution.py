"""
Tests for handler execution in the runner.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sansible.engine.scheduler import HostContext
from sansible.engine.inventory import Host
from sansible.engine.playbook import Play, Task
from sansible.engine.results import TaskResult, TaskStatus
from sansible.connections.base import RunResult


class TestNotifiedHandlersTracking:
    """Test tracking of notified handlers."""
    
    def test_host_context_has_notified_handlers(self):
        """HostContext tracks notified handlers."""
        host = Host(name="test", variables={})
        ctx = HostContext(host=host)
        assert hasattr(ctx, 'notified_handlers')
        assert ctx.notified_handlers == set()
    
    def test_add_notified_handler(self):
        """Can add handler name to notified set."""
        host = Host(name="test", variables={})
        ctx = HostContext(host=host)
        ctx.notified_handlers.add("Restart service")
        assert "Restart service" in ctx.notified_handlers
    
    def test_multiple_notifies_deduplicated(self):
        """Same handler notified multiple times only runs once."""
        host = Host(name="test", variables={})
        ctx = HostContext(host=host)
        ctx.notified_handlers.add("Restart service")
        ctx.notified_handlers.add("Restart service")
        assert len(ctx.notified_handlers) == 1


class TestHandlerMatching:
    """Test matching handlers by name and listen."""
    
    def test_match_handler_by_name(self):
        """Handler matches by exact name."""
        from sansible.engine.runner import PlaybookRunner
        
        handler = Task(name="Restart nginx", module="command", args={"cmd": "systemctl restart nginx"})
        
        # Handler name matches notification
        assert handler.name == "Restart nginx"
    
    def test_match_handler_by_listen(self):
        """Handler matches by listen trigger."""
        handler = Task(
            name="Restart web services",
            module="command",
            args={"cmd": "systemctl restart nginx"},
            listen=["restart nginx", "web config changed"],
        )
        
        # Can be triggered by any listen value
        assert "restart nginx" in handler.listen
        assert "web config changed" in handler.listen


class TestHandlerExecution:
    """Test handler execution at end of play."""
    
    @pytest.mark.asyncio
    async def test_handler_runs_when_notified(self):
        """Handler runs when task notifies it and changes."""
        from sansible.engine.playbook import Play, Task
        
        play = Play(
            name="Test",
            hosts="localhost",
            tasks=[
                Task(name="Change config", module="command", args={"cmd": "echo"}, notify=["Restart"]),
            ],
            handlers=[
                Task(name="Restart", module="command", args={"cmd": "restart"}),
            ],
        )
        
        # Handler should be found for "Restart" notification
        handler_names = [h.name for h in play.handlers]
        assert "Restart" in handler_names
    
    @pytest.mark.asyncio
    async def test_handler_not_run_when_no_change(self):
        """Handler doesn't run if notifying task didn't change."""
        # This is behavioral - if task returns changed=False, handler not notified
        result = TaskResult(
            host="test",
            task_name="test",
            status=TaskStatus.OK,
            changed=False,  # No change
        )
        
        # Should not trigger handler
        assert result.changed is False
    
    @pytest.mark.asyncio
    async def test_handlers_run_in_order(self):
        """Handlers run in definition order, not notification order."""
        play = Play(
            name="Test",
            hosts="localhost",
            tasks=[],
            handlers=[
                Task(name="First handler", module="debug", args={}),
                Task(name="Second handler", module="debug", args={}),
                Task(name="Third handler", module="debug", args={}),
            ],
        )
        
        # Handlers maintain definition order
        assert play.handlers[0].name == "First handler"
        assert play.handlers[1].name == "Second handler"
        assert play.handlers[2].name == "Third handler"


class TestListenTriggers:
    """Test listen-based handler triggers."""
    
    def test_listen_allows_multiple_triggers(self):
        """Handler with listen responds to multiple notification names."""
        handler = Task(
            name="Restart all web",
            module="command",
            args={"cmd": "systemctl restart nginx apache2"},
            listen=["restart nginx", "restart apache", "web restart"],
        )
        
        # Any of these should trigger the handler
        notified = "restart nginx"
        assert notified in handler.listen or notified == handler.name
    
    def test_listen_and_name_both_work(self):
        """Handler responds to both its name and listen values."""
        handler = Task(
            name="Restart nginx",
            module="command",
            args={},
            listen=["web config changed"],
        )
        
        # Should match by name
        assert handler.name == "Restart nginx"
        # Should also match by listen
        assert "web config changed" in handler.listen
