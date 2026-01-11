"""
Sansible Module Base

Base class and registry for all modules.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional, Type

from sansible.engine.playbook import Task
from sansible.engine.results import TaskResult, TaskStatus
from sansible.engine.scheduler import HostContext


@dataclass
class ModuleResult:
    """Result of module execution."""
    
    changed: bool = False
    rc: int = 0
    stdout: str = ""
    stderr: str = ""
    msg: str = ""
    failed: bool = False
    skipped: bool = False
    results: Dict[str, Any] = field(default_factory=dict)
    
    def to_task_result(self, host: str, task_name: str) -> TaskResult:
        """Convert to TaskResult."""
        if self.skipped:
            status = TaskStatus.SKIPPED
        elif self.failed:
            status = TaskStatus.FAILED
        elif self.changed:
            status = TaskStatus.CHANGED
        else:
            status = TaskStatus.OK
        
        return TaskResult(
            host=host,
            task_name=task_name,
            status=status,
            changed=self.changed,
            rc=self.rc,
            stdout=self.stdout,
            stderr=self.stderr,
            msg=self.msg,
            results=self.results,
        )


class Module(ABC):
    """
    Base class for all modules.
    
    Modules implement task execution logic for specific operations.
    """
    
    # Module name (used for registration)
    name: str = ""
    
    # Required arguments
    required_args: List[str] = []
    
    # Optional arguments with defaults
    optional_args: Dict[str, Any] = {}
    
    def __init__(self, args: Dict[str, Any], context: HostContext):
        self.args = args
        self.context = context
        self.connection = context.connection
    
    def validate_args(self) -> Optional[str]:
        """
        Validate module arguments.
        
        Returns:
            Error message if validation fails, None otherwise
        """
        for required in self.required_args:
            if required not in self.args:
                return f"Missing required argument: {required}"
        return None
    
    def get_arg(self, name: str, default: Any = None) -> Any:
        """Get an argument value with optional default."""
        if name in self.args:
            return self.args[name]
        if name in self.optional_args:
            return self.optional_args[name]
        return default
    
    def wrap_become(self, cmd: str) -> str:
        """Wrap command with privilege escalation if become is enabled."""
        if not self.context.become:
            return cmd
        
        method = self.context.become_method
        user = self.context.become_user
        
        if method == "sudo":
            return f"sudo -u {user} {cmd}"
        elif method == "su":
            return f"su - {user} -c '{cmd}'"
        else:
            # Default to sudo
            return f"sudo -u {user} {cmd}"

    @abstractmethod
    async def run(self) -> ModuleResult:
        """
        Execute the module.
        
        Returns:
            ModuleResult with execution outcome
        """
        pass


# Module registry
_modules: Dict[str, Type[Module]] = {}
_modules_imported = False


def register_module(cls: Type[Module]) -> Type[Module]:
    """Decorator to register a module class."""
    _modules[cls.name] = cls
    return cls


def get_module(name: str) -> Optional[Type[Module]]:
    """Get a module class by name."""
    _ensure_modules_imported()
    return _modules.get(name)


def _ensure_modules_imported() -> None:
    """Ensure all modules have been imported."""
    global _modules_imported
    if not _modules_imported:
        _import_builtin_modules()
        _modules_imported = True


class ModuleRegistry:
    """Static class for module registry access."""
    
    @staticmethod
    def get(name: str) -> Optional[Type[Module]]:
        """Get a module class by name."""
        return get_module(name)
    
    @staticmethod
    def list() -> List[str]:
        """List all registered module names."""
        _ensure_modules_imported()
        return list(_modules.keys())
    
    @staticmethod
    def register(cls: Type[Module]) -> Type[Module]:
        """Register a module class."""
        return register_module(cls)


def list_modules() -> List[str]:
    """List all registered module names."""
    return list(_modules.keys())


def create_module_runner(
    verbose: int = 0,
    json_output: bool = False,
) -> Callable[[Task, HostContext, Dict[str, Any]], Coroutine[Any, Any, TaskResult]]:
    """
    Create a module runner function for the scheduler.
    
    Args:
        verbose: Verbosity level
        json_output: If True, suppress console output
        
    Returns:
        Async callable that runs modules
    """
    # Import modules to register them
    _import_builtin_modules()
    
    async def runner(
        task: Task,
        ctx: HostContext,
        rendered_args: Dict[str, Any],
    ) -> TaskResult:
        """Run a module on a host."""
        module_class = get_module(task.module)
        
        if module_class is None:
            return TaskResult(
                host=ctx.host.name,
                task_name=task.name,
                status=TaskStatus.FAILED,
                msg=f"Unknown module: {task.module}",
            )
        
        # Create module instance
        module = module_class(rendered_args, ctx)
        
        # Validate arguments
        error = module.validate_args()
        if error:
            return TaskResult(
                host=ctx.host.name,
                task_name=task.name,
                status=TaskStatus.FAILED,
                msg=error,
            )
        
        # Print task banner
        if not json_output:
            _print_task_banner(task.name)
        
        # Run module
        try:
            result = await module.run()
        except Exception as e:
            result = ModuleResult(
                failed=True,
                msg=str(e),
            )
        
        task_result = result.to_task_result(ctx.host.name, task.name)
        
        # Print result
        if not json_output:
            _print_task_result(task_result, verbose)
        
        return task_result
    
    return runner


def _import_builtin_modules() -> None:
    """Import all built-in modules to register them."""
    # These imports trigger the @register_module decorators
    from sansible.modules import builtin_command
    from sansible.modules import builtin_shell
    from sansible.modules import builtin_raw
    from sansible.modules import builtin_copy
    from sansible.modules import builtin_debug
    from sansible.modules import builtin_set_fact
    from sansible.modules import builtin_fail
    from sansible.modules import builtin_assert
    from sansible.modules import builtin_file
    from sansible.modules import builtin_template
    from sansible.modules import win_command
    from sansible.modules import win_shell
    from sansible.modules import win_copy
    from sansible.modules import win_file
    from sansible.modules import win_service
    from sansible.modules import builtin_setup
    from sansible.modules import builtin_stat
    from sansible.modules import win_stat
    from sansible.modules import builtin_lineinfile
    from sansible.modules import win_lineinfile
    from sansible.modules import builtin_wait_for
    from sansible.modules import win_wait_for


def _print_task_banner(task_name: str) -> None:
    """Print task banner."""
    print(f"\nTASK [{task_name}] " + "*" * max(0, 60 - len(task_name) - 8))


def _print_task_result(result: TaskResult, verbose: int = 0) -> None:
    """Print task result."""
    if result.status == TaskStatus.OK:
        color = "\033[32m"  # Green
        status = "ok"
    elif result.status == TaskStatus.CHANGED:
        color = "\033[33m"  # Yellow
        status = "changed"
    elif result.status == TaskStatus.SKIPPED:
        color = "\033[36m"  # Cyan
        status = "skipped"
    else:
        color = "\033[31m"  # Red
        status = "failed"
    
    reset = "\033[0m"
    
    line = f"{color}{status}: [{result.host}]{reset}"
    
    if result.msg and (result.failed or verbose > 0):
        line += f" => {result.msg}"
    
    print(line)
    
    if verbose >= 2 and result.stdout:
        print(f"  stdout: {result.stdout[:200]}")
    if verbose >= 1 and result.stderr:
        print(f"  stderr: {result.stderr[:200]}")
