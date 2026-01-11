"""
Sansible Scheduler

Async execution scheduler with fork-style parallelism using asyncio.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from sansible.engine.inventory import Host
from sansible.engine.playbook import Play, Task
from sansible.engine.results import (
    HostStats,
    PlaybookResult,
    PlayResult,
    TaskResult,
    TaskStatus,
)
from sansible.engine.templating import evaluate_when, render_recursive


@dataclass
class HostContext:
    """Runtime context for a single host during playbook execution."""
    
    host: Host
    vars: Dict[str, Any] = field(default_factory=dict)
    registered_vars: Dict[str, Any] = field(default_factory=dict)
    failed: bool = False
    unreachable: bool = False
    connection: Any = None  # Connection object (set during execution)
    check_mode: bool = False  # Dry-run mode
    diff_mode: bool = False  # Show diffs
    become: bool = False  # Privilege escalation
    become_user: str = "root"  # Target user for become
    become_method: str = "sudo"  # Method: sudo, su, runas
    notified_handlers: Set[str] = field(default_factory=set)  # Handlers to run
    failed_blocks: Set[str] = field(default_factory=set)  # Blocks that failed
    rescued_blocks: Set[str] = field(default_factory=set)  # Blocks that were rescued
    
    def get_vars(self) -> Dict[str, Any]:
        """Get all variables for templating."""
        merged = {}
        merged.update(self.host.get_vars())
        merged.update(self.vars)
        merged.update(self.registered_vars)
        return merged
    
    def register_result(self, name: str, result: TaskResult) -> None:
        """Register a task result for later use."""
        self.registered_vars[name] = {
            'changed': result.changed,
            'rc': result.rc,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'stdout_lines': result.stdout.splitlines() if result.stdout else [],
            'stderr_lines': result.stderr.splitlines() if result.stderr else [],
            'failed': result.failed,
            'msg': result.msg,
            **result.results,
        }


class Scheduler:
    """
    Async scheduler for playbook execution.
    
    Uses asyncio with a semaphore to limit concurrency (like Ansible's forks).
    Executes tasks in "linear" strategy: for each task, run across all hosts
    in parallel (up to forks limit), then proceed to next task.
    """
    
    def __init__(
        self,
        forks: int = 5,
        connection_factory: Optional[Callable] = None,
    ):
        """
        Initialize the scheduler.
        
        Args:
            forks: Maximum number of parallel host executions
            connection_factory: Async callable to create connections: (host) -> Connection
        """
        self.forks = max(1, forks)
        self.connection_factory = connection_factory
        self._semaphore: Optional[asyncio.Semaphore] = None
    
    async def run_playbook(
        self,
        plays: List[Play],
        hosts: List[Host],
        playbook_path: str,
        module_runner: Callable,
    ) -> PlaybookResult:
        """
        Run a playbook.
        
        Args:
            plays: List of Play objects to execute
            hosts: List of Host objects (resolved from inventory)
            playbook_path: Path to playbook (for result reporting)
            module_runner: Async callable to run modules: (task, host_ctx) -> TaskResult
            
        Returns:
            PlaybookResult with all execution results
        """
        result = PlaybookResult(playbook_path=playbook_path)
        
        for play in plays:
            play_result = await self.run_play(play, hosts, module_runner)
            result.add_play_result(play_result)
            
            # If all hosts failed, stop
            if all(s.has_failures for s in play_result.host_stats.values()):
                break
        
        return result
    
    async def run_play(
        self,
        play: Play,
        all_hosts: List[Host],
        module_runner: Callable,
    ) -> PlayResult:
        """
        Run a single play.
        
        Args:
            play: Play object to execute
            all_hosts: All available hosts
            module_runner: Async callable to run modules
            
        Returns:
            PlayResult with task results for this play
        """
        # Filter hosts for this play
        target_hosts = self._filter_hosts(play.hosts, all_hosts)
        
        if not target_hosts:
            return PlayResult(
                play_name=play.name,
                hosts=[],
            )
        
        # Initialize host contexts
        host_contexts = {
            host.name: HostContext(
                host=host,
                vars=play.vars.copy(),
            )
            for host in target_hosts
        }
        
        # Create connections
        if self.connection_factory:
            await self._create_connections(host_contexts)
        
        play_result = PlayResult(
            play_name=play.name,
            hosts=[h.name for h in target_hosts],
        )
        
        # Run tasks in linear order
        for task in play.tasks:
            task_results = await self.run_task(task, host_contexts, module_runner)
            for task_result in task_results:
                play_result.add_result(task_result)
        
        # Close connections
        await self._close_connections(host_contexts)
        
        return play_result
    
    async def run_task(
        self,
        task: Task,
        host_contexts: Dict[str, HostContext],
        module_runner: Callable,
    ) -> List[TaskResult]:
        """
        Run a single task across all hosts.
        
        Args:
            task: Task to execute
            host_contexts: Dict of host name -> HostContext
            module_runner: Async callable to run modules
            
        Returns:
            List of TaskResult objects (one per host)
        """
        self._semaphore = asyncio.Semaphore(self.forks)
        
        # Filter out failed hosts
        active_contexts = {
            name: ctx for name, ctx in host_contexts.items()
            if not ctx.failed and not ctx.unreachable
        }
        
        if not active_contexts:
            return []
        
        # Create coroutines for each host
        async def run_on_host(ctx: HostContext) -> TaskResult:
            async with self._semaphore:
                return await self._execute_task_on_host(task, ctx, module_runner)
        
        # Run in parallel
        coros = [run_on_host(ctx) for ctx in active_contexts.values()]
        results = await asyncio.gather(*coros, return_exceptions=True)
        
        # Convert exceptions to failed results
        final_results = []
        for i, result in enumerate(results):
            host_name = list(active_contexts.keys())[i]
            if isinstance(result, Exception):
                final_results.append(TaskResult(
                    host=host_name,
                    task_name=task.name,
                    status=TaskStatus.FAILED,
                    msg=str(result),
                ))
                host_contexts[host_name].failed = True
            else:
                final_results.append(result)
                if result.status == TaskStatus.FAILED:
                    host_contexts[host_name].failed = True
                elif result.status == TaskStatus.UNREACHABLE:
                    host_contexts[host_name].unreachable = True
        
        return final_results
    
    async def _execute_task_on_host(
        self,
        task: Task,
        ctx: HostContext,
        module_runner: Callable,
    ) -> TaskResult:
        """Execute a single task on a single host."""
        host_vars = ctx.get_vars()
        
        # Evaluate when condition
        if task.when:
            try:
                should_run = evaluate_when(task.when, host_vars)
                if not should_run:
                    return TaskResult(
                        host=ctx.host.name,
                        task_name=task.name,
                        status=TaskStatus.SKIPPED,
                        msg="Conditional check failed",
                    )
            except Exception as e:
                return TaskResult(
                    host=ctx.host.name,
                    task_name=task.name,
                    status=TaskStatus.FAILED,
                    msg=f"When condition error: {e}",
                )
        
        # Handle loops
        if task.loop is not None:
            return await self._execute_loop(task, ctx, module_runner)
        
        # Render task args
        try:
            rendered_args = render_recursive(task.args, host_vars)
        except Exception as e:
            return TaskResult(
                host=ctx.host.name,
                task_name=task.name,
                status=TaskStatus.FAILED,
                msg=f"Template error in task args: {e}",
            )
        
        # Run the module
        try:
            result = await module_runner(task, ctx, rendered_args)
        except Exception as e:
            result = TaskResult(
                host=ctx.host.name,
                task_name=task.name,
                status=TaskStatus.FAILED,
                msg=str(e),
            )
        
        # Handle ignore_errors
        if result.status == TaskStatus.FAILED and task.ignore_errors:
            result.status = TaskStatus.OK
            result.msg = f"(ignored) {result.msg}"
        
        # Handle changed_when / failed_when
        if task.changed_when is not None and result.ok:
            try:
                # Add result vars for evaluation
                eval_vars = {**host_vars, 'result': result.to_dict()}
                changed = evaluate_when(task.changed_when, eval_vars)
                result.changed = changed
                result.status = TaskStatus.CHANGED if changed else TaskStatus.OK
            except Exception:
                pass  # Ignore evaluation errors for changed_when
        
        if task.failed_when is not None:
            try:
                eval_vars = {**host_vars, 'result': result.to_dict()}
                failed = evaluate_when(task.failed_when, eval_vars)
                if failed:
                    result.status = TaskStatus.FAILED
            except Exception:
                pass
        
        # Register result if requested
        if task.register:
            ctx.register_result(task.register, result)
        
        return result
    
    async def _execute_loop(
        self,
        task: Task,
        ctx: HostContext,
        module_runner: Callable,
    ) -> TaskResult:
        """Execute a task with a loop."""
        host_vars = ctx.get_vars()
        
        # Render the loop items
        try:
            loop_items = render_recursive(task.loop, host_vars)
        except Exception as e:
            return TaskResult(
                host=ctx.host.name,
                task_name=task.name,
                status=TaskStatus.FAILED,
                msg=f"Template error in loop: {e}",
            )
        
        if not isinstance(loop_items, list):
            loop_items = [loop_items]
        
        loop_results = []
        overall_changed = False
        overall_failed = False
        
        for item in loop_items:
            # Add item to vars
            item_vars = {**host_vars, task.loop_var: item}
            
            # Render task args with item
            try:
                rendered_args = render_recursive(task.args, item_vars)
            except Exception as e:
                loop_results.append(TaskResult(
                    host=ctx.host.name,
                    task_name=task.name,
                    status=TaskStatus.FAILED,
                    msg=f"Template error: {e}",
                ))
                overall_failed = True
                if not task.ignore_errors:
                    break
                continue
            
            # Run the module
            try:
                result = await module_runner(task, ctx, rendered_args)
            except Exception as e:
                result = TaskResult(
                    host=ctx.host.name,
                    task_name=task.name,
                    status=TaskStatus.FAILED,
                    msg=str(e),
                )
            
            loop_results.append(result)
            
            if result.changed:
                overall_changed = True
            if result.failed:
                if task.ignore_errors:
                    result.status = TaskStatus.OK
                else:
                    overall_failed = True
                    break
        
        # Combine results
        combined = TaskResult(
            host=ctx.host.name,
            task_name=task.name,
            status=TaskStatus.FAILED if overall_failed else (
                TaskStatus.CHANGED if overall_changed else TaskStatus.OK
            ),
            changed=overall_changed,
            loop_results=loop_results,
            msg=f"Loop completed with {len(loop_results)} iterations",
        )
        
        # Register combined results
        if task.register:
            ctx.register_result(task.register, combined)
            # Also add 'results' list for compatibility
            ctx.registered_vars[task.register]['results'] = [
                r.to_dict() for r in loop_results
            ]
        
        return combined
    
    def _filter_hosts(self, pattern: str, hosts: List[Host]) -> List[Host]:
        """Filter hosts based on play's hosts pattern."""
        if pattern == "all":
            return hosts
        
        # Simple pattern matching
        matching = []
        patterns = [p.strip() for p in pattern.split(',')]
        
        for host in hosts:
            for p in patterns:
                if p == host.name or p in host.groups:
                    matching.append(host)
                    break
        
        return matching
    
    async def _create_connections(self, host_contexts: Dict[str, HostContext]) -> None:
        """Create connections for all hosts."""
        if not self.connection_factory:
            return
        
        async def create_conn(ctx: HostContext) -> None:
            try:
                ctx.connection = await self.connection_factory(ctx.host)
            except Exception as e:
                ctx.unreachable = True
                ctx.failed = True
        
        await asyncio.gather(*[create_conn(ctx) for ctx in host_contexts.values()])
    
    async def _close_connections(self, host_contexts: Dict[str, HostContext]) -> None:
        """Close all connections."""
        for ctx in host_contexts.values():
            if ctx.connection is not None:
                try:
                    if hasattr(ctx.connection, 'close'):
                        close_result = ctx.connection.close()
                        if asyncio.iscoroutine(close_result):
                            await close_result
                except Exception:
                    pass
