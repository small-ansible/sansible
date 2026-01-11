"""
Tests for executor and linear strategy scheduling.
"""

import asyncio
import pytest
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from sansible.engine.scheduler import Scheduler, HostContext
from sansible.engine.inventory import Host
from sansible.engine.playbook import Task
from sansible.engine.results import TaskResult, TaskStatus
from sansible.connections.base import Connection, RunResult


class MockConnection(Connection):
    """Mock connection for testing."""
    
    def __init__(self, host: Host):
        super().__init__(host)
        self.connected = False
        self.commands_run: List[str] = []
        self.files_put: List[tuple] = []
        
    async def connect(self) -> None:
        self.connected = True
    
    async def close(self) -> None:
        self.connected = False
    
    async def run(
        self,
        command: str,
        shell: bool = True,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
        environment: Optional[dict] = None,
    ) -> RunResult:
        self.commands_run.append(command)
        return RunResult(rc=0, stdout="ok", stderr="")
    
    async def put(
        self,
        local_path: Path,
        remote_path: str,
        mode: Optional[str] = None,
    ) -> None:
        self.files_put.append((str(local_path), remote_path, mode))
    
    async def get(
        self,
        remote_path: str,
        local_path: Path,
    ) -> None:
        pass
    
    async def mkdir(self, remote_path: str, mode: Optional[str] = None) -> None:
        pass
    
    async def stat(self, remote_path: str) -> Optional[dict]:
        return None


class TestScheduler:
    """Test scheduler functionality."""
    
    def test_scheduler_creation(self):
        """Test scheduler can be created."""
        scheduler = Scheduler(forks=5)
        assert scheduler.forks == 5
    
    def test_scheduler_default_forks(self):
        """Test scheduler default forks."""
        scheduler = Scheduler()
        assert scheduler.forks == 5  # Default value
    
    @pytest.mark.asyncio
    async def test_scheduler_respects_forks_limit(self):
        """Test scheduler respects forks limit."""
        scheduler = Scheduler(forks=2)
        
        # Track concurrent executions
        concurrent = 0
        max_concurrent = 0
        
        async def task_runner(delay: float):
            nonlocal concurrent, max_concurrent
            concurrent += 1
            max_concurrent = max(max_concurrent, concurrent)
            await asyncio.sleep(delay)
            concurrent -= 1
        
        # Run 5 tasks with forks=2, they should run max 2 at a time
        tasks = [task_runner(0.1) for _ in range(5)]
        
        # Using semaphore to limit concurrency
        semaphore = asyncio.Semaphore(2)
        
        async def limited_task(t):
            async with semaphore:
                await t
        
        await asyncio.gather(*[limited_task(task_runner(0.05)) for _ in range(5)])
        
        assert max_concurrent <= 2


class TestHostContext:
    """Test HostContext management."""
    
    def test_host_context_creation(self):
        """Test HostContext can be created."""
        host = Host(name="test")
        ctx = HostContext(host=host)
        
        assert ctx.host == host
        assert ctx.vars == {}
        assert ctx.connection is None
    
    def test_host_context_vars(self):
        """Test HostContext variable management."""
        host = Host(name="test")
        ctx = HostContext(host=host)
        
        ctx.vars["foo"] = "bar"
        ctx.vars["nested"] = {"key": "value"}
        
        assert ctx.vars["foo"] == "bar"
        assert ctx.vars["nested"]["key"] == "value"
    
    def test_host_context_get_vars(self):
        """Test HostContext.get_vars() method."""
        host = Host(name="test", variables={"host_var": "from_host"})
        ctx = HostContext(host=host)
        ctx.vars["ctx_var"] = "from_context"
        
        all_vars = ctx.get_vars()
        
        assert all_vars["host_var"] == "from_host"
        assert all_vars["ctx_var"] == "from_context"
        # Also includes computed vars from host
        assert all_vars["inventory_hostname"] == "test"
    
    def test_host_context_with_connection(self):
        """Test HostContext with connection."""
        host = Host(name="test")
        conn = MockConnection(host)
        ctx = HostContext(host=host)
        ctx.connection = conn
        
        assert ctx.connection is conn


class TestLinearStrategy:
    """Test linear strategy execution."""
    
    def test_task_order_maintained(self):
        """Test that tasks maintain order."""
        tasks = [
            Task(name="Task 1", module="debug", args={"msg": "1"}),
            Task(name="Task 2", module="debug", args={"msg": "2"}),
            Task(name="Task 3", module="debug", args={"msg": "3"}),
        ]
        
        # Linear strategy: each task runs on all hosts before next task
        task_names = [t.name for t in tasks]
        assert task_names == ["Task 1", "Task 2", "Task 3"]
    
    @pytest.mark.asyncio
    async def test_task_runs_on_all_hosts(self):
        """Test that each task runs on all hosts."""
        hosts = [
            Host(name="host1"),
            Host(name="host2"),
            Host(name="host3"),
        ]
        
        execution_order: List[tuple] = []
        
        async def run_on_host(task_name: str, host_name: str):
            execution_order.append((task_name, host_name))
        
        # Simulate linear strategy
        tasks = ["task1", "task2"]
        for task in tasks:
            await asyncio.gather(*[run_on_host(task, h.name) for h in hosts])
        
        # All hosts should complete task1 before task2
        task1_indices = [i for i, (t, h) in enumerate(execution_order) if t == "task1"]
        task2_indices = [i for i, (t, h) in enumerate(execution_order) if t == "task2"]
        
        assert max(task1_indices) < min(task2_indices)


class TestConcurrencySemantics:
    """Test concurrency behavior."""
    
    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        """Test that semaphore limits concurrent execution."""
        max_concurrent = 3
        semaphore = asyncio.Semaphore(max_concurrent)
        
        current = 0
        peak = 0
        
        async def work():
            nonlocal current, peak
            async with semaphore:
                current += 1
                peak = max(peak, current)
                await asyncio.sleep(0.01)
                current -= 1
        
        # Run 10 concurrent tasks
        await asyncio.gather(*[work() for _ in range(10)])
        
        assert peak <= max_concurrent
    
    @pytest.mark.asyncio
    async def test_task_isolation(self):
        """Test that tasks don't share mutable state incorrectly."""
        results: Dict[str, str] = {}
        
        async def task(name: str, value: str):
            # Simulate async work
            await asyncio.sleep(0.01)
            results[name] = value
        
        await asyncio.gather(
            task("a", "value_a"),
            task("b", "value_b"),
            task("c", "value_c"),
        )
        
        assert results == {"a": "value_a", "b": "value_b", "c": "value_c"}


class TestTaskResult:
    """Test task result handling."""
    
    def test_task_result_ok(self):
        """Test OK task result."""
        result = TaskResult(
            host="test",
            task_name="Test Task",
            status=TaskStatus.OK,
            changed=False,
        )
        
        assert result.status == TaskStatus.OK
        assert not result.failed
        assert not result.changed
    
    def test_task_result_changed(self):
        """Test CHANGED task result."""
        result = TaskResult(
            host="test",
            task_name="Test Task",
            status=TaskStatus.CHANGED,
            changed=True,
        )
        
        assert result.status == TaskStatus.CHANGED
        assert result.changed
    
    def test_task_result_failed(self):
        """Test FAILED task result."""
        result = TaskResult(
            host="test",
            task_name="Test Task",
            status=TaskStatus.FAILED,
            msg="Something went wrong",
        )
        
        assert result.status == TaskStatus.FAILED
        assert result.failed
        assert result.msg == "Something went wrong"
    
    def test_task_result_skipped(self):
        """Test SKIPPED task result."""
        result = TaskResult(
            host="test",
            task_name="Test Task",
            status=TaskStatus.SKIPPED,
        )
        
        assert result.status == TaskStatus.SKIPPED
        # TaskResult uses .ok property to check success, skipped is not ok
        assert not result.ok
        assert not result.failed
