"""
Sansible Playbook Runner

High-level runner that coordinates inventory, playbook parsing,
connections, module execution, and output.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from sansible.connections.base import Connection
from sansible.connections.local import LocalConnection
from sansible.engine.inventory import InventoryManager, Host
from sansible.engine.playbook import PlaybookParser, Play, Task
from sansible.engine.results import (
    PlaybookResult,
    PlayResult,
    TaskResult,
    TaskStatus,
    HostStats,
)
from sansible.engine.scheduler import Scheduler, HostContext
from sansible.engine.templating import TemplateEngine, render_recursive, evaluate_when
from sansible.engine.errors import SansibleError, ParseError, UnsupportedFeatureError, ModuleError
from sansible.modules.base import Module, ModuleResult, ModuleRegistry
from sansible.galaxy.loader import GalaxyModuleLoader
from sansible.galaxy.module import GalaxyModule


class PlaybookRunner:
    """
    High-level playbook runner.
    
    Coordinates:
    - Inventory loading and host selection
    - Playbook parsing
    - Connection creation
    - Module execution
    - Output formatting
    """
    
    def __init__(
        self,
        inventory_source: str,
        playbook_paths: List[str],
        forks: int = 5,
        limit: Optional[str] = None,
        check_mode: bool = False,
        diff_mode: bool = False,
        verbosity: int = 0,
        extra_vars: Optional[Dict[str, Any]] = None,
        json_output: bool = False,
        vault_password: Optional[str] = None,
        vault_password_file: Optional[str] = None,
    ):
        self.inventory_source = inventory_source
        self.playbook_paths = playbook_paths
        self.forks = forks
        self.limit = limit
        self.check_mode = check_mode
        self.diff_mode = diff_mode
        self.verbosity = verbosity
        self.extra_vars = extra_vars or {}
        self.json_output = json_output
        self.vault_password = vault_password
        self.vault_password_file = vault_password_file
        
        # Components
        self.inventory: Optional[InventoryManager] = None
        self.template_engine = TemplateEngine()
        self.scheduler = Scheduler(forks=forks)
        self._vault = None
        
        # Connection cache
        self._connections: Dict[str, Connection] = {}
        
        # Initialize vault if password provided
        self._init_vault()
    
    def _init_vault(self) -> None:
        """Initialize vault decryption if password is provided."""
        if not self.vault_password and not self.vault_password_file:
            return
        
        from sansible.engine.vault import VaultLib, VaultSecret
        
        self._vault = VaultLib()
        
        if self.vault_password_file:
            secret = VaultSecret.from_file(self.vault_password_file)
            self._vault.add_secret(secret)
        
        if self.vault_password:
            self._vault.add_secret(VaultSecret(self.vault_password))
    
    def run(self) -> int:
        """
        Run playbooks synchronously.
        
        Returns:
            Exit code (0=success, 2=host failures, 3=parse error, 4=unsupported)
        """
        try:
            result = asyncio.run(self.run_async())
            
            # Output JSON if requested
            if self.json_output:
                print(result.to_json())
            
            return self._get_exit_code(result)
        except ParseError as e:
            if self.json_output:
                self._print_json_error("parse_error", str(e), 3)
            else:
                self._print_error(f"Parse error: {e}")
            return 3
        except UnsupportedFeatureError as e:
            if self.json_output:
                self._print_json_error("unsupported_feature", str(e), 4)
            else:
                self._print_error(f"Unsupported feature: {e}")
            return 4
        except SansibleError as e:
            if self.json_output:
                self._print_json_error("error", str(e), 1)
            else:
                self._print_error(f"Error: {e}")
            return 1
        except KeyboardInterrupt:
            if self.json_output:
                self._print_json_error("interrupted", "Execution interrupted", 130)
            else:
                self._print_error("\nInterrupted")
            return 130
    
    def _print_json_error(self, error_type: str, message: str, exit_code: int) -> None:
        """Print an error in JSON format."""
        import json
        error_obj = {
            "error": True,
            "error_type": error_type,
            "message": message,
            "exit_code": exit_code,
        }
        print(json.dumps(error_obj, indent=2))
    
    async def run_async(self) -> PlaybookResult:
        """Run playbooks asynchronously."""
        # Load inventory
        self._print_header("Loading inventory...")
        self.inventory = InventoryManager()
        self.inventory.parse(self.inventory_source)
        
        all_results: List[PlayResult] = []
        host_stats: Dict[str, HostStats] = {}
        
        # Process each playbook
        for playbook_path in self.playbook_paths:
            self._print_header(f"\nPLAYBOOK: {playbook_path}")
            
            # Parse playbook
            parser = PlaybookParser(playbook_path)
            plays = parser.parse()
            
            # Run each play
            for play in plays:
                play_result = await self._run_play(play, playbook_path)
                all_results.append(play_result)
                
                # Aggregate host stats
                for host, stats in play_result.host_stats.items():
                    if host not in host_stats:
                        host_stats[host] = HostStats(host=host)
                    host_stats[host].merge(stats)
        
        # Close all connections
        await self._close_connections()
        
        # Print recap
        self._print_recap(host_stats)
        
        # Create final result - use first playbook path for now
        playbook_result = PlaybookResult(playbook_path=self.playbook_paths[0])
        playbook_result.play_results = all_results
        return playbook_result
    
    async def _run_play(self, play: Play, playbook_path: str) -> PlayResult:
        """Run a single play."""
        self._print_play(play)
        
        # Resolve hosts for this play
        hosts = self._resolve_hosts(play.hosts)
        
        if not hosts:
            self._print_warning(f"No hosts matched for play: {play.hosts}")
            return PlayResult(
                play_name=play.name,
                hosts=[],
                tasks=[],
                host_stats={},
            )
        
        # Create host contexts
        host_contexts: Dict[str, HostContext] = {}
        for host in hosts:
            ctx = HostContext(
                host=host,
                check_mode=self.check_mode,
                diff_mode=self.diff_mode,
            )
            # Add play vars
            ctx.vars.update(play.vars)
            # Add extra vars (highest priority)
            ctx.vars.update(self.extra_vars)
            host_contexts[host.name] = ctx
        
        # Ensure connections
        await self._ensure_connections(hosts, host_contexts)
        
        # Gather facts if requested
        if play.gather_facts:
            await self._gather_facts(host_contexts)
        
        # Run tasks
        task_results: List[Dict[str, TaskResult]] = []
        all_task_results: List[TaskResult] = []
        
        for task in play.tasks:
            task_result = await self._run_task(task, host_contexts)
            task_results.append(task_result)
            # Flatten for JSON output
            for host_result in task_result.values():
                all_task_results.append(host_result)
        
        # Calculate host stats
        host_stats = self._calculate_stats(task_results, list(host_contexts.keys()))
        
        return PlayResult(
            play_name=play.name,
            hosts=[h.name for h in hosts],
            task_results=all_task_results,  # Include for JSON output
            host_stats=host_stats,
        )
    
    async def _run_task(
        self,
        task: Task,
        host_contexts: Dict[str, HostContext],
    ) -> Dict[str, TaskResult]:
        """Run a task across all hosts."""
        self._print_task(task)
        
        results: Dict[str, TaskResult] = {}
        
        # Create coroutines for each host
        async def run_on_host(host_name: str) -> TaskResult:
            ctx = host_contexts[host_name]
            
            # Skip if host already failed
            if ctx.failed:
                return TaskResult(
                    host=host_name,
                    task_name=task.name,
                    status=TaskStatus.SKIPPED,
                    msg="Host previously failed",
                )
            
            # Evaluate 'when' condition
            if task.when:
                try:
                    should_run = evaluate_when(task.when, ctx.get_vars())
                    if not should_run:
                        self._print_host_result(host_name, "skipped", "conditional")
                        return TaskResult(
                            host=host_name,
                            task_name=task.name,
                            status=TaskStatus.SKIPPED,
                            msg="Conditional check failed",
                        )
                except Exception as e:
                    return TaskResult(
                        host=host_name,
                        task_name=task.name,
                        status=TaskStatus.FAILED,
                        msg=f"Error evaluating 'when': {e}",
                    )
            
            # Handle loops
            if task.loop:
                return await self._run_task_loop(task, ctx)
            
            # Run single execution
            return await self._run_task_single(task, ctx)
        
        # Run across all hosts with concurrency limit
        semaphore = asyncio.Semaphore(self.forks)
        
        async def run_with_semaphore(host_name: str) -> tuple:
            async with semaphore:
                result = await run_on_host(host_name)
                return host_name, result
        
        tasks = [run_with_semaphore(name) for name in host_contexts.keys()]
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        for item in completed:
            if isinstance(item, Exception):
                # Handle unexpected exceptions
                continue
            host_name, result = item
            results[host_name] = result
            
            # Update host context - only mark as failed if ignore_errors is False
            if result.status == TaskStatus.FAILED and not task.ignore_errors:
                host_contexts[host_name].failed = True
            
            # Register result if requested
            if task.register:
                host_contexts[host_name].register_result(task.register, result)
        
        return results
    
    async def _run_task_single(self, task: Task, ctx: HostContext) -> TaskResult:
        """Run a single task execution (no loop)."""
        try:
            # Handle task-level check_mode override
            original_check_mode = ctx.check_mode
            if task.check_mode is not None:
                ctx.check_mode = task.check_mode
            
            # Handle delegate_to - execute on a different host
            effective_ctx = ctx
            delegate_connection = None
            
            if task.delegate_to:
                delegate_target = render_recursive(task.delegate_to, ctx.get_vars())
                if isinstance(delegate_target, str):
                    delegate_target = delegate_target.strip()
                    
                    # Get or create connection for delegate host
                    if delegate_target in self._connections:
                        delegate_connection = self._connections[delegate_target]
                    else:
                        # Create a temporary host for the delegate target
                        if delegate_target in ('localhost', '127.0.0.1'):
                            # Local delegation
                            from sansible.engine.inventory import Host
                            delegate_host = Host(delegate_target, {'ansible_connection': 'local'})
                            delegate_connection = LocalConnection(delegate_host)
                        elif self.inventory and delegate_target in self.inventory.hosts:
                            # Known inventory host
                            delegate_host = self.inventory.hosts[delegate_target]
                            delegate_connection = self._create_connection(delegate_host)
                        else:
                            # Unknown host - create minimal host with SSH
                            from sansible.engine.inventory import Host
                            delegate_host = Host(delegate_target, {'ansible_connection': 'ssh'})
                            delegate_connection = self._create_connection(delegate_host)
                        
                        # Connect if not already connected
                        await delegate_connection.connect()
                        self._connections[delegate_target] = delegate_connection
                    
                    # Create a new context for the delegate host but keep original vars
                    from sansible.engine.inventory import Host
                    delegate_host_obj = (
                        self.inventory.hosts[delegate_target] 
                        if self.inventory and delegate_target in self.inventory.hosts 
                        else Host(delegate_target)
                    )
                    effective_ctx = HostContext(
                        host=delegate_host_obj,
                        check_mode=ctx.check_mode,
                        diff_mode=ctx.diff_mode,
                    )
                    effective_ctx.vars = ctx.vars.copy()
                    effective_ctx.vars['ansible_delegated_vars'] = {
                        'ansible_host': delegate_target,
                    }
                    effective_ctx.connection = delegate_connection
            
            # Template the args
            templated_args = render_recursive(task.args, effective_ctx.get_vars())
            
            # Module resolution logic
            module = None
            module_class = None
            
            # Check if this is a Galaxy FQCN (namespace.collection.module format)
            if GalaxyModuleLoader.is_galaxy_module(task.module):
                # Try to map to native Sansible module first
                native_name = self._fqcn_to_native_module(task.module)
                if native_name:
                    module_class = ModuleRegistry.get(native_name)
                
                if module_class:
                    # Use native Sansible implementation
                    module = module_class(templated_args, effective_ctx)
                else:
                    # Use Galaxy module execution (requires Ansible on target)
                    # Check if target is Windows - Galaxy execution won't work
                    is_windows = effective_ctx.host.get_variable('ansible_os_family', '').lower() == 'windows' or \
                                 effective_ctx.host.get_variable('ansible_connection', '') == 'winrm'
                    if is_windows:
                        return TaskResult(
                            host=ctx.host.name,
                            task_name=task.name,
                            status=TaskStatus.FAILED,
                            msg=f"Galaxy module '{task.module}' cannot be executed on Windows targets. "
                                f"Ansible control node cannot run on Windows. Use native Sansible win_* modules instead.",
                        )
                    module = GalaxyModule(task.module, templated_args, effective_ctx)
            else:
                # Standard module lookup
                module_class = ModuleRegistry.get(task.module)
                if not module_class:
                    return TaskResult(
                        host=ctx.host.name,
                        task_name=task.name,
                        status=TaskStatus.FAILED,
                        msg=f"Unknown module: {task.module}",
                    )
                module = module_class(templated_args, effective_ctx)
            
            # Validate args
            validation_error = module.validate_args()
            if validation_error:
                return TaskResult(
                    host=ctx.host.name,
                    task_name=task.name,
                    status=TaskStatus.FAILED,
                    msg=validation_error,
                )
            
            # Check mode handling
            if self.check_mode and hasattr(module, 'check'):
                result = await module.check()
            else:
                result = await module.run()
            
            # Report result using original host name
            task_result = result.to_task_result(ctx.host.name, task.name)
            
            # Add delegate info to result if delegated
            if task.delegate_to:
                task_result.results['delegate_to'] = task.delegate_to
            
            # For debug module or verbose mode, show the message
            show_msg = (
                task_result.status == TaskStatus.FAILED or
                task.module == 'debug' or
                self.verbosity > 0
            )
            
            self._print_host_result(
                ctx.host.name,
                task_result.status.value,
                task_result.msg if show_msg else None,
            )
            return task_result
            
        except Exception as e:
            self._print_host_result(ctx.host.name, "failed", str(e))
            return TaskResult(
                host=ctx.host.name,
                task_name=task.name,
                status=TaskStatus.FAILED,
                msg=str(e),
            )
        finally:
            # Restore original check_mode if it was overridden
            if task.check_mode is not None:
                ctx.check_mode = original_check_mode
    
    async def _run_task_loop(self, task: Task, ctx: HostContext) -> TaskResult:
        """Run a task with loop."""
        loop_items = task.loop
        loop_var = task.loop_control.get('loop_var', 'item') if task.loop_control else 'item'
        
        all_changed = False
        all_results = []
        
        for idx, item in enumerate(loop_items):
            # Add loop variables
            loop_vars = ctx.vars.copy()
            loop_vars[loop_var] = item
            loop_vars['ansible_loop'] = {
                'index': idx,
                'index0': idx,
                'first': idx == 0,
                'last': idx == len(loop_items) - 1,
                'length': len(loop_items),
            }
            
            # Create a temporary context with loop vars
            temp_ctx = HostContext(
                host=ctx.host,
                check_mode=ctx.check_mode,
                diff_mode=ctx.diff_mode,
            )
            temp_ctx.vars = loop_vars
            temp_ctx.registered_vars = ctx.registered_vars
            temp_ctx.connection = ctx.connection
            
            # Run the task
            result = await self._run_task_single(task, temp_ctx)
            all_results.append(result)
            
            if result.changed:
                all_changed = True
            
            if result.status == TaskStatus.FAILED and not task.ignore_errors:
                # Stop loop on failure
                return TaskResult(
                    host=ctx.host.name,
                    task_name=task.name,
                    status=TaskStatus.FAILED,
                    changed=all_changed,
                    msg=result.msg,
                    results={'results': [r.__dict__ for r in all_results]},
                )
        
        # All loop iterations succeeded
        return TaskResult(
            host=ctx.host.name,
            task_name=task.name,
            status=TaskStatus.CHANGED if all_changed else TaskStatus.OK,
            changed=all_changed,
            results={'results': [r.__dict__ for r in all_results]},
        )
    
    def _resolve_hosts(self, pattern: str) -> List[Host]:
        """Resolve host pattern to list of hosts."""
        if not self.inventory:
            return []
        
        hosts = self.inventory.get_hosts(pattern)
        
        # Apply limit if specified
        if self.limit:
            limit_hosts = self.inventory.get_hosts(self.limit)
            limit_names = {h.name for h in limit_hosts}
            hosts = [h for h in hosts if h.name in limit_names]
        
        return hosts
    
    async def _ensure_connections(
        self,
        hosts: List[Host],
        contexts: Dict[str, HostContext],
    ) -> None:
        """Ensure connections are established for all hosts."""
        for host in hosts:
            if host.name not in self._connections:
                conn = self._create_connection(host)
                try:
                    await conn.connect()
                    self._connections[host.name] = conn
                except Exception as e:
                    contexts[host.name].unreachable = True
                    contexts[host.name].failed = True
                    self._print_warning(f"Failed to connect to {host.name}: {e}")
                    continue
            
            contexts[host.name].connection = self._connections[host.name]
    
    def _create_connection(self, host: Host) -> Connection:
        """Create a connection for a host based on connection type."""
        conn_type = host.get_variable('ansible_connection', 'ssh')
        
        if conn_type == 'local':
            return LocalConnection(host)
        elif conn_type == 'ssh':
            from sansible.connections.ssh_asyncssh import SSHConnection
            return SSHConnection(host)
        elif conn_type in ('winrm', 'psrp'):
            from sansible.connections.winrm_psrp import WinRMConnection
            return WinRMConnection(host)
        else:
            # Default to local for localhost
            if host.name in ('localhost', '127.0.0.1'):
                return LocalConnection(host)
            # Default to SSH
            from sansible.connections.ssh_asyncssh import SSHConnection
            return SSHConnection(host)
    
    async def _close_connections(self) -> None:
        """Close all connections."""
        for conn in self._connections.values():
            try:
                await conn.close()
            except Exception:
                pass
        self._connections.clear()
    
    async def _gather_facts(self, host_contexts: Dict[str, HostContext]) -> None:
        """Gather facts from all hosts using the setup module."""
        self._print_task_banner("Gathering Facts")
        
        from sansible.modules.builtin_setup import SetupModule
        
        for host_name, ctx in host_contexts.items():
            if ctx.failed or ctx.unreachable or not ctx.connection:
                continue
            
            try:
                module = SetupModule({}, ctx)
                result = await module.run()
                
                if result.failed:
                    self._print_host_result(host_name, "failed", result.msg)
                    continue
                
                # Store facts in context
                facts = result.results.get("ansible_facts", {})
                ctx.vars.update(facts)
                ctx.vars["ansible_facts"] = facts
                
                self._print_host_result(host_name, "ok", "")
            except Exception as e:
                self._print_warning(f"Failed to gather facts from {host_name}: {e}")
    
    def _print_task_banner(self, task_name: str) -> None:
        """Print task banner."""
        if not self.json_output:
            print(f"\nTASK [{task_name}] " + "*" * max(0, 60 - len(task_name) - 8))

    def _calculate_stats(
        self,
        task_results: List[Dict[str, TaskResult]],
        host_names: List[str],
    ) -> Dict[str, HostStats]:
        """Calculate host statistics from task results."""
        stats: Dict[str, HostStats] = {}
        
        for host in host_names:
            stats[host] = HostStats(host=host)
        
        for task_result_map in task_results:
            for host, result in task_result_map.items():
                if host not in stats:
                    stats[host] = HostStats(host=host)
                
                if result.status == TaskStatus.OK:
                    stats[host].ok += 1
                elif result.status == TaskStatus.CHANGED:
                    stats[host].changed += 1
                elif result.status == TaskStatus.FAILED:
                    stats[host].failed += 1
                elif result.status == TaskStatus.SKIPPED:
                    stats[host].skipped += 1
                elif result.status == TaskStatus.UNREACHABLE:
                    stats[host].unreachable += 1
        
        return stats
    
    def _get_exit_code(self, result: PlaybookResult) -> int:
        """Determine exit code from playbook result."""
        final_stats = result.get_final_stats()
        for stats in final_stats.values():
            if stats.failed > 0 or stats.unreachable > 0:
                return 2
        return 0
    
    # Output methods (suppressed when json_output is True)
    def _print_header(self, msg: str) -> None:
        """Print a header message."""
        if not self.json_output:
            print(msg)
    
    def _print_play(self, play: Play) -> None:
        """Print play banner."""
        if not self.json_output:
            print(f"\nPLAY [{play.name}] " + "*" * 50)
    
    def _print_task(self, task: Task) -> None:
        """Print task banner."""
        if not self.json_output:
            print(f"\nTASK [{task.name}] " + "-" * 50)
    
    def _print_host_result(
        self,
        host: str,
        status: str,
        msg: Optional[str] = None,
    ) -> None:
        """Print result for a host."""
        if self.json_output:
            return
            
        colors = {
            'ok': '\033[32m',      # Green
            'changed': '\033[33m', # Yellow
            'failed': '\033[31m',  # Red
            'skipped': '\033[36m', # Cyan
        }
        reset = '\033[0m'
        
        color = colors.get(status, '')
        
        if msg:
            print(f"{color}{status}: [{host}]{reset} => {msg}")
        else:
            print(f"{color}{status}: [{host}]{reset}")
    
    def _print_warning(self, msg: str) -> None:
        """Print a warning message."""
        if not self.json_output:
            print(f"\033[33m[WARNING]: {msg}\033[0m", file=sys.stderr)
    
    def _fqcn_to_native_module(self, fqcn: str) -> Optional[str]:
        """
        Map a Galaxy FQCN to its native Sansible module name if available.
        
        Examples:
            ansible.builtin.copy -> copy
            ansible.windows.win_ping -> win_ping
            ansible.builtin.debug -> debug
            
        Returns:
            Native module name if mapping exists, None otherwise.
        """
        parts = fqcn.split('.')
        if len(parts) != 3:
            return None
            
        namespace, collection, module_name = parts
        
        # ansible.builtin.* -> module_name (copy, file, etc.)
        if namespace == 'ansible' and collection == 'builtin':
            return module_name
        
        # ansible.windows.* -> module_name (already win_* prefixed)
        if namespace == 'ansible' and collection == 'windows':
            return module_name
        
        # ansible.posix.* -> module_name (if we have native implementations)
        if namespace == 'ansible' and collection == 'posix':
            return module_name
            
        # Other collections - no native mapping
        return None
    
    def _print_error(self, msg: str) -> None:
        """Print an error message (always print, even with JSON mode - errors go to stderr)."""
        if not self.json_output:
            print(f"\033[31m{msg}\033[0m", file=sys.stderr)
    
    def _print_recap(self, host_stats: Dict[str, HostStats]) -> None:
        """Print final recap."""
        if self.json_output:
            return
            
        print("\nPLAY RECAP " + "*" * 60)
        
        for host, stats in sorted(host_stats.items()):
            status_parts = []
            
            if stats.ok:
                status_parts.append(f"\033[32mok={stats.ok}\033[0m")
            if stats.changed:
                status_parts.append(f"\033[33mchanged={stats.changed}\033[0m")
            if stats.failed:
                status_parts.append(f"\033[31mfailed={stats.failed}\033[0m")
            if stats.skipped:
                status_parts.append(f"\033[36mskipped={stats.skipped}\033[0m")
            if stats.unreachable:
                status_parts.append(f"\033[31munreachable={stats.unreachable}\033[0m")
            
            status_str = "  ".join(status_parts) if status_parts else "ok=0"
            print(f"{host:40} : {status_str}")
