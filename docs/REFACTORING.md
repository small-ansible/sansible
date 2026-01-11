# Sansible Code Analysis & Refactoring Recommendations

> Comprehensive analysis of the sansible codebase at version 0.4.0  
> Generated: January 2026

## Executive Summary

Sansible is a well-architected, minimal Ansible runner with **952 lines in the main runner**, **768 lines in playbook parser**, and **63 modules**. The codebase follows good practices overall but has opportunities for improvement in code deduplication, abstraction, and maintainability.

### Key Findings

| Category | Rating | Summary |
|----------|--------|---------|
| **Architecture** | ⭐⭐⭐⭐ | Clean separation of concerns, well-defined layers |
| **Type Hints** | ⭐⭐⭐⭐ | Comprehensive usage, some improvements possible |
| **Error Handling** | ⭐⭐⭐ | Good exception hierarchy, some overly broad catches |
| **Code Duplication** | ⭐⭐⭐ | Significant duplication in modules |
| **Documentation** | ⭐⭐⭐⭐ | Good docstrings, could improve inline comments |
| **Test Coverage** | ⭐⭐⭐⭐ | 28 unit test files, good coverage of core features |

---

## 1. Code Structure Analysis

### 1.1 Architecture Overview

The codebase follows a clean layered architecture:

```
CLI Layer (cli/)
    ↓
Engine Layer (engine/)
    ├── runner.py (952 lines) — Main orchestrator
    ├── playbook.py (768 lines) — YAML parsing
    ├── scheduler.py (451 lines) — Async execution
    ├── templating.py (559 lines) — Jinja2 rendering
    └── inventory.py (679 lines) — Host management
    ↓
Connection Layer (connections/)
    ├── base.py — Abstract interface
    ├── local.py — Local execution
    ├── ssh_asyncssh.py — SSH via asyncssh
    └── winrm_psrp.py — WinRM via pypsrp
    ↓
Module Layer (modules/)
    └── 60+ modules for Linux/Windows
```

**Strengths:**
- Clear separation between CLI, engine, connections, and modules
- Well-defined abstract base classes (`Connection`, `Module`)
- Consistent async/await pattern throughout

**Areas for Improvement:**
- `runner.py` is a "god class" at 952 lines — could be decomposed
- Some cross-layer dependencies (modules importing from engine)

### 1.2 Code Duplication Analysis

#### Critical: Module Connection Checks

**Every module** contains the same boilerplate:

```python
# Found in 25+ modules
if not self.connection:
    return ModuleResult(
        failed=True,
        msg="No connection available",
    )
```

**Recommendation:** Move to base class as a decorator or pre-run check:

```python
# In modules/base.py
class Module(ABC):
    def _require_connection(self) -> Optional[ModuleResult]:
        """Return failure result if no connection, else None."""
        if not self.connection:
            return ModuleResult(failed=True, msg="No connection available")
        return None
    
    async def execute(self) -> ModuleResult:
        """Template method with connection check."""
        if (error := self._require_connection()):
            return error
        return await self.run()
```

Or use a decorator:

```python
def requires_connection(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not self.connection:
            return ModuleResult(failed=True, msg="No connection available")
        return await func(self, *args, **kwargs)
    return wrapper
```

#### Duplication: Check Mode Handling

Similar pattern repeated across modules:

```python
# Found in 15+ modules
if self.context.check_mode:
    return ModuleResult(
        changed=True,
        msg=f"... would be ... (check mode)",
        results={...},
    )
```

**Recommendation:** Create a helper method:

```python
# In modules/base.py
def check_mode_result(self, action: str, **results) -> ModuleResult:
    """Return a standard check mode result."""
    return ModuleResult(
        changed=True,
        msg=f"{action} (check mode)",
        results=results,
    )
```

#### Duplication: Linux vs Windows Modules

`builtin_file.py` (251 lines) and `win_file.py` (206 lines) share significant logic:
- Both check for state (absent, directory, touch, file)
- Both handle mode/permissions
- Different only in command execution

**Recommendation:** Create a shared abstraction:

```python
# modules/file_base.py
class BaseFileModule(Module):
    """Shared logic for file/directory operations."""
    
    @abstractmethod
    def _build_remove_command(self, path: str, is_dir: bool) -> str:
        """Platform-specific remove command."""
        pass
    
    async def _ensure_absent(self, path: str) -> ModuleResult:
        stat = await self.connection.stat(path)
        if not stat or not stat.get("exists"):
            return ModuleResult(changed=False, msg="Already absent")
        
        cmd = self._build_remove_command(path, stat.get("isdir", False))
        result = await self.connection.run(cmd)
        # ... shared logic
```

### 1.3 Separation of Concerns Issues

#### runner.py is Too Large

The `PlaybookRunner` class handles too many responsibilities:

1. Inventory loading
2. Playbook parsing coordination
3. Connection management
4. Task execution
5. Output formatting
6. Statistics calculation
7. Handler execution
8. Galaxy module resolution

**Recommendation:** Extract into focused classes:

```python
# Proposed structure
class ConnectionManager:
    """Manages connection lifecycle and pooling."""
    async def get_connection(self, host: Host) -> Connection: ...
    async def close_all(self) -> None: ...

class OutputFormatter:
    """Handles all console/JSON output."""
    def print_play(self, play: Play) -> None: ...
    def print_recap(self, stats: Dict[str, HostStats]) -> None: ...

class TaskExecutor:
    """Executes individual tasks on hosts."""
    async def run_task(self, task: Task, contexts: Dict) -> Dict[str, TaskResult]: ...

class PlaybookRunner:
    """Coordinates playbook execution using composed helpers."""
    def __init__(self, ...):
        self.connections = ConnectionManager(...)
        self.output = OutputFormatter(...)
        self.executor = TaskExecutor(...)
```

---

## 2. Best Practices Review

### 2.1 Type Hints Usage

**Current State:** Good coverage with some gaps

**Strengths:**
- All public methods have return type hints
- Complex types properly annotated (`Dict[str, Any]`, `Optional[str]`)
- Type aliases used appropriately

**Issues Found:**

1. **Inconsistent Optional usage:**
```python
# Some files use | None (Python 3.10+)
def validate_args(self) -> str | None:

# Others use Optional (older style)
def get_variable(self, key: str, default: Any = None) -> Any:
```

2. **Missing type hints on class attributes:**
```python
# In base.py - class attributes lack type annotations
class Module(ABC):
    name: str = ""
    required_args: List[str] = []  # ✓ Good
    optional_args: Dict[str, Any] = {}  # ✓ Good

# But some modules override without hints:
class CopyModule(Module):
    optional_args = {  # Missing type hint
        "dest": None,
        ...
    }
```

**Recommendation:** Standardize on `X | None` syntax (requires Python 3.10+, which is fine given `>=3.9` requirement in pyproject.toml). Add `from __future__ import annotations` at top of files for consistency.

### 2.2 Error Handling Patterns

**Strengths:**
- Well-defined exception hierarchy in [errors.py](src/sansible/engine/errors.py)
- Exit codes match Ansible behavior (0, 2, 3, 4)
- Custom exceptions carry context (file path, line number)

**Issues Found:**

1. **Overly Broad Exception Catches:**

Found 40+ instances of `except Exception as e:` that could be more specific:

```python
# In templating.py - catches everything
try:
    result = subprocess.run(...)
except Exception as e:
    raise TemplateError(f"lookup('pipe'): Error executing {command}: {e}")
```

**Better approach:**
```python
except subprocess.SubprocessError as e:
    raise TemplateError(f"lookup('pipe'): Subprocess error: {e}")
except OSError as e:
    raise TemplateError(f"lookup('pipe'): OS error: {e}")
```

2. **Silent Exception Swallowing:**

```python
# In runner.py line 775
async def _close_connections(self) -> None:
    for conn in self._connections.values():
        try:
            await conn.close()
        except Exception:
            pass  # Silently ignored
```

**Recommendation:** At minimum, log at debug level:
```python
except Exception as e:
    if self.verbosity >= 2:
        self._print_warning(f"Error closing connection: {e}")
```

3. **Inconsistent Exception Types in Connections:**

```python
# ssh_asyncssh.py raises ConnectionError
from sansible.engine.errors import ConnectionError
raise ConnectionError(host=self.host.name, message=str(e), connection_type='ssh')

# But some paths return RunResult with error instead
return RunResult(rc=1, stdout="", stderr=str(e))
```

### 2.3 Async/Await Consistency

**Strengths:**
- All modules use `async def run()`
- Connection methods are properly async
- Semaphore-based concurrency limiting

**Issues Found:**

1. **Sync Code in Async Context (WinRM):**

```python
# winrm_psrp.py - runs sync code in executor
async def connect(self) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, self._sync_connect)
```

This is correct but could be documented better. The pypsrp library is synchronous, so this wrapping is necessary.

2. **Missing Timeout Handling:**

```python
# Some async operations don't have timeouts
await sftp.put(str(local_path), remote_path)  # Could hang indefinitely
```

**Recommendation:** Wrap with `asyncio.wait_for()`:
```python
await asyncio.wait_for(
    sftp.put(str(local_path), remote_path),
    timeout=self.host.get_variable('ansible_timeout', 30)
)
```

### 2.4 Documentation Quality

**Strengths:**
- Module docstrings explain purpose and supported features
- Function docstrings include Args/Returns sections
- `AI_HANDOFF.md` and `copilot-instructions.md` are excellent

**Gaps:**
- Some complex algorithms lack inline comments
- Magic numbers/strings not always documented

```python
# Example: what does 700 mean?
CHUNK_SIZE = 700 * 1024  # Should have comment explaining WinRM limit

# Better:
# WinRM has a ~1MB message size limit; 700KB leaves room for base64 overhead
CHUNK_SIZE = 700 * 1024
```

---

## 3. Potential Issues

### 3.1 Complex Functions Needing Decomposition

#### `_run_task_single()` - 150+ lines

This method handles:
- Check mode override
- Delegate_to resolution
- Template rendering
- Galaxy module detection
- Native module lookup
- Argument validation
- Execution
- Result formatting

**Recommendation:** Extract logical chunks:

```python
async def _run_task_single(self, task: Task, ctx: HostContext) -> TaskResult:
    # Prepare execution context
    effective_ctx = await self._prepare_context(task, ctx)
    
    # Resolve and instantiate module
    module = await self._resolve_module(task, effective_ctx)
    if isinstance(module, TaskResult):
        return module  # Error result
    
    # Execute with proper mode handling
    return await self._execute_module(module, task, ctx)
```

#### `_parse_play()` - Complex Nesting

The play parsing has deep nesting for vars_files, roles, tasks, handlers, etc.

**Recommendation:** Extract into private methods:

```python
def _parse_play(self, data: Dict[str, Any]) -> Play:
    self._validate_play_data(data)
    play = self._create_play_from_data(data)
    play.vars = self._load_play_vars(data)
    play.tasks = self._load_all_tasks(data)
    play.handlers = self._load_handlers(data)
    return play
```

### 3.2 Missing Abstractions

#### 1. Command Builder Pattern

Many modules construct shell commands with string concatenation:

```python
# Current approach - error-prone
cmd = f'rm -rf "{path}"'
cmd = f"systemctl start {name}"
cmd = f"Get-Service -Name '{name}'"
```

**Recommendation:** Create command builders:

```python
class ShellCommand:
    """Safe shell command builder."""
    
    @staticmethod
    def rm(path: str, recursive: bool = False, force: bool = False) -> str:
        flags = []
        if recursive:
            flags.append("-r")
        if force:
            flags.append("-f")
        return f"rm {' '.join(flags)} {shlex.quote(path)}"

class PowerShellCommand:
    """Safe PowerShell command builder."""
    
    @staticmethod
    def get_service(name: str) -> str:
        return f"Get-Service -Name '{name.replace(\"'\", \"''\")}'"
```

#### 2. Result Factory

Modules create `ModuleResult` objects with repetitive patterns:

```python
# Create a factory for common patterns
class ResultFactory:
    @staticmethod
    def success(msg: str = "", changed: bool = False, **results) -> ModuleResult:
        return ModuleResult(changed=changed, msg=msg, results=results)
    
    @staticmethod
    def failure(msg: str, rc: int = 1, stderr: str = "") -> ModuleResult:
        return ModuleResult(failed=True, msg=msg, rc=rc, stderr=stderr)
    
    @staticmethod
    def skipped(msg: str = "skipped") -> ModuleResult:
        return ModuleResult(skipped=True, msg=msg)
```

### 3.3 Hard-Coded Values

| Location | Value | Recommendation |
|----------|-------|----------------|
| [scheduler.py](src/sansible/engine/scheduler.py) | `forks=5` | Already configurable ✓ |
| [runner.py](src/sansible/engine/runner.py#L120) | `max_iterations = 10` | Make configurable constant |
| [winrm_psrp.py](src/sansible/connections/winrm_psrp.py) | `CHUNK_SIZE = 700 * 1024` | Move to config or host var |
| [ssh_asyncssh.py](src/sansible/connections/ssh_asyncssh.py) | `timeout=30` | Good - from host var |
| [galaxy/loader.py](src/sansible/galaxy/loader.py) | `MIN_ANSIBLE_VERSION = "2.14.0"` | Consider making configurable |

**Recommendation:** Create a `config.py` module:

```python
# engine/config.py
from dataclasses import dataclass

@dataclass
class ExecutionConfig:
    max_template_iterations: int = 10
    default_timeout: int = 30
    winrm_chunk_size: int = 700 * 1024
    min_galaxy_ansible_version: str = "2.14.0"

# Global singleton, can be overridden for testing
config = ExecutionConfig()
```

### 3.4 Inconsistent Patterns

#### State Machine for File Operations

Both `file` and `win_file` modules use if/elif chains for state handling:

```python
if state == "absent":
    return await self._ensure_absent(path)
elif state == "directory":
    return await self._ensure_directory(path, mode, recurse)
elif state == "touch":
    ...
```

**Recommendation:** Use a dispatch table:

```python
_STATE_HANDLERS = {
    "absent": "_ensure_absent",
    "directory": "_ensure_directory",
    "touch": "_ensure_touch",
    "file": "_ensure_file",
    "link": "_ensure_link",
}

async def run(self) -> ModuleResult:
    handler_name = self._STATE_HANDLERS.get(state)
    if not handler_name:
        return ModuleResult(failed=True, msg=f"Unknown state: {state}")
    handler = getattr(self, handler_name)
    return await handler(path, **kwargs)
```

---

## 4. Performance Considerations

### 4.1 Connection Pooling

**Current Implementation:** Connections are cached in `self._connections: Dict[str, Connection]`

**Strengths:**
- Connections reused across tasks
- Closed at playbook end

**Potential Improvements:**

1. **No connection timeout/keepalive:**
```python
# SSH connections may go stale during long playbooks
# Consider implementing keepalive pings
async def _keepalive_connections(self) -> None:
    for conn in self._connections.values():
        if hasattr(conn, 'ping'):
            await conn.ping()
```

2. **No connection limits per host:**
```python
# For delegate_to, new connections are created without limit
# Consider a connection pool per host
```

### 4.2 Unnecessary Blocking Operations

1. **File Reading in Templating:**
```python
# lookup functions read files synchronously
def _lookup_file(path: str, **kwargs) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()  # Blocks event loop
```

**Recommendation:** Use `aiofiles` or run in executor:
```python
async def _lookup_file_async(path: str, **kwargs) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _lookup_file_sync, path, kwargs)
```

2. **YAML Parsing:**
```python
# Large playbooks parsed synchronously
content = self.playbook_path.read_text(encoding='utf-8')
documents = list(yaml.safe_load_all(content))
```

For very large playbooks, consider async parsing. However, this is likely not a practical bottleneck.

### 4.3 Memory Usage Patterns

1. **Task Results Accumulation:**
```python
# All results kept in memory
all_results: List[PlayResult] = []
task_results: List[Dict[str, TaskResult]] = []
```

For large playbooks with many hosts, this could grow significantly.

**Recommendation:** Consider streaming results to JSON output:
```python
class StreamingPlaybookResult:
    def __init__(self, output_file: Optional[Path] = None):
        self.output_file = output_file
    
    def add_result(self, result: TaskResult) -> None:
        if self.output_file:
            # Append to file instead of keeping in memory
            with open(self.output_file, 'a') as f:
                f.write(json.dumps(result.to_dict()) + '\n')
```

2. **Galaxy Host State Cache:**
```python
# Class-level cache grows indefinitely
_host_states: Dict[str, GalaxyHostState] = {}
```

**Recommendation:** Limit cache size or use WeakValueDictionary.

---

## 5. Maintainability

### 5.1 Test Coverage Analysis

**Current Test Files (28):**
```
tests/unit/
├── test_become.py          ✓ Privilege escalation
├── test_block.py           ✓ Block parsing
├── test_block_execution.py ✓ Block execution with rescue/always
├── test_check_diff_mode.py ✓ Check and diff modes
├── test_cli.py             ✓ CLI argument parsing
├── test_compat_scan.py     ✓ Compatibility scanner
├── test_dynamic_inventory.py ✓ Dynamic inventory scripts
├── test_executor_linear.py ✓ Linear strategy execution
├── test_fs.py              ✓ Platform filesystem utils
├── test_galaxy.py          ✓ Galaxy module loading
├── test_gather_facts.py    ✓ Setup module / facts
├── test_handler_execution.py ✓ Handler notification
├── test_handlers.py        ✓ Handler parsing
├── test_include_import.py  ✓ Task includes/imports
├── test_inventory_ini.py   ✓ INI inventory parsing
├── test_lineinfile_module.py ✓ lineinfile module
├── test_lookup_functions.py ✓ Lookup plugins
├── test_paths.py           ✓ Path utilities
├── test_playbook_roles.py  ✓ Role loading
├── test_proc.py            ✓ Process utilities
├── test_script_module.py   ✓ Script module
├── test_stat_module.py     ✓ Stat module
├── test_tags_limit.py      ✓ Tag/limit filtering
├── test_vault.py           ✓ Vault decryption
├── test_wait_for_module.py ✓ wait_for module
├── test_win_service.py     ✓ Windows service module
└── test_win_template_module.py ✓ Windows template
```

**Coverage Gaps:**

| Missing Tests | Priority | Notes |
|---------------|----------|-------|
| `test_runner.py` | High | Core orchestrator untested in isolation |
| `test_templating.py` | High | Complex Jinja2 logic |
| `test_connections.py` | Medium | Connection base class |
| `test_results.py` | Low | Simple dataclasses |
| Individual modules (copy, file, etc.) | Medium | Many modules lack unit tests |

**Recommendation:** Add test coverage for:
1. `PlaybookRunner` with mocked components
2. Edge cases in `templating.py` (recursive rendering, filter chains)
3. Connection error handling paths

### 5.2 Code Complexity Hotspots

Using cognitive complexity as a metric:

| File | Function | Est. Complexity | Issue |
|------|----------|-----------------|-------|
| [runner.py](src/sansible/engine/runner.py) | `_run_task_single` | High | 150+ lines, many branches |
| [runner.py](src/sansible/engine/runner.py) | `_run_play` | Medium-High | Block/rescue/always tracking |
| [playbook.py](src/sansible/engine/playbook.py) | `_parse_play` | High | Deep nesting for all play sections |
| [playbook.py](src/sansible/engine/playbook.py) | `_parse_block` | Medium | Recursive with metadata |
| [templating.py](src/sansible/engine/templating.py) | `evaluate_when` | Medium | Many condition formats |
| [inventory.py](src/sansible/engine/inventory.py) | `_parse_ini_file` | High | Complex INI parsing |

### 5.3 Documentation Needs

1. **Architecture Decision Records (ADRs):**
   - Why asyncssh over Paramiko?
   - Why pypsrp over pywinrm?
   - Why linear strategy only (no free)?

2. **Module Development Guide:**
   - How to add a new module
   - Testing patterns for modules
   - Windows vs Linux considerations

3. **Inline Documentation:**
   - Complex algorithms in `_render_vars_iteratively()`
   - Block execution state machine

---

## 6. Recommended Refactoring Priorities

### Phase 1: Quick Wins (Low Risk, High Impact)

1. **Extract connection check to base class**
   - Affects: 25+ modules
   - Effort: 2 hours
   - Risk: Low

2. **Add `check_mode_result()` helper**
   - Affects: 15+ modules
   - Effort: 1 hour
   - Risk: Low

3. **Create command builder utilities**
   - Affects: All modules with shell commands
   - Effort: 4 hours
   - Risk: Low

### Phase 2: Medium Effort Improvements

4. **Decompose `runner.py`**
   - Extract `ConnectionManager`
   - Extract `OutputFormatter`
   - Effort: 8 hours
   - Risk: Medium (needs thorough testing)

5. **Create shared `FileModuleBase`**
   - Unify `file` and `win_file`
   - Effort: 6 hours
   - Risk: Medium

6. **Improve error specificity**
   - Replace broad `except Exception` with specific types
   - Effort: 4 hours
   - Risk: Low

### Phase 3: Larger Refactors

7. **Add configuration management**
   - Create `config.py` with all constants
   - Environment variable overrides
   - Effort: 4 hours
   - Risk: Low

8. **Add async file I/O for lookups**
   - Install `aiofiles` or use executors
   - Effort: 3 hours
   - Risk: Medium

9. **Add connection keepalive**
   - Ping mechanism for long playbooks
   - Effort: 4 hours
   - Risk: Medium

---

## 7. Code Examples for Key Refactors

### 7.1 Module Base Class Enhancement

```python
# modules/base.py - Enhanced version

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Dict, List, Optional, Type

@dataclass
class ModuleResult:
    """Result of module execution."""
    changed: bool = False
    failed: bool = False
    skipped: bool = False
    rc: int = 0
    stdout: str = ""
    stderr: str = ""
    msg: str = ""
    results: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def success(cls, msg: str = "", changed: bool = False, **results) -> "ModuleResult":
        return cls(changed=changed, msg=msg, results=results)
    
    @classmethod
    def failure(cls, msg: str, rc: int = 1, stderr: str = "") -> "ModuleResult":
        return cls(failed=True, msg=msg, rc=rc, stderr=stderr)
    
    @classmethod
    def skip(cls, msg: str = "skipped") -> "ModuleResult":
        return cls(skipped=True, msg=msg)


def requires_connection(func):
    """Decorator to ensure connection exists before running module."""
    @wraps(func)
    async def wrapper(self: "Module", *args, **kwargs):
        if not self.connection:
            return ModuleResult.failure("No connection available")
        return await func(self, *args, **kwargs)
    return wrapper


class Module(ABC):
    """Base class for all modules with enhanced helpers."""
    
    name: str = ""
    required_args: List[str] = []
    optional_args: Dict[str, Any] = {}
    
    def __init__(self, args: Dict[str, Any], context: "HostContext"):
        self.args = args
        self.context = context
        self.connection = context.connection if context else None
    
    def check_mode_skip(self, action: str, **results) -> Optional[ModuleResult]:
        """Return check mode result if in check mode, else None."""
        if self.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"{action} (check mode)",
                results=results,
            )
        return None
    
    @property
    def check_mode(self) -> bool:
        return self.context.check_mode if self.context else False
    
    @abstractmethod
    async def run(self) -> ModuleResult:
        """Execute the module."""
        pass
```

### 7.2 Connection Manager Extraction

```python
# engine/connection_manager.py

from typing import Dict, Optional
from sansible.connections.base import Connection
from sansible.engine.inventory import Host

class ConnectionManager:
    """Manages connection lifecycle and pooling."""
    
    def __init__(
        self,
        connection_type: Optional[str] = None,
        timeout: int = 30,
        remote_user: Optional[str] = None,
        private_key_file: Optional[str] = None,
    ):
        self._connections: Dict[str, Connection] = {}
        self.connection_type = connection_type
        self.timeout = timeout
        self.remote_user = remote_user
        self.private_key_file = private_key_file
    
    async def get(self, host: Host) -> Connection:
        """Get or create a connection for a host."""
        if host.name not in self._connections:
            conn = self._create(host)
            await conn.connect()
            self._connections[host.name] = conn
        return self._connections[host.name]
    
    def _create(self, host: Host) -> Connection:
        """Create appropriate connection for host type."""
        conn_type = self.connection_type or host.ansible_connection
        
        if conn_type == 'local':
            from sansible.connections.local import LocalConnection
            return LocalConnection(host)
        elif conn_type == 'ssh':
            from sansible.connections.ssh_asyncssh import SSHConnection
            return SSHConnection(host)
        elif conn_type in ('winrm', 'psrp'):
            from sansible.connections.winrm_psrp import WinRMConnection
            return WinRMConnection(host)
        else:
            raise ValueError(f"Unknown connection type: {conn_type}")
    
    async def close_all(self) -> None:
        """Close all open connections."""
        for conn in self._connections.values():
            try:
                await conn.close()
            except Exception:
                pass
        self._connections.clear()
```

### 7.3 Command Builder Example

```python
# platform/commands.py

import shlex
from abc import ABC, abstractmethod
from typing import List, Optional

class CommandBuilder(ABC):
    """Abstract command builder for platform-specific commands."""
    
    @abstractmethod
    def remove(self, path: str, recursive: bool = False) -> str:
        pass
    
    @abstractmethod
    def create_directory(self, path: str, mode: Optional[str] = None) -> str:
        pass


class UnixCommandBuilder(CommandBuilder):
    """Unix/Linux command builder with proper escaping."""
    
    @staticmethod
    def quote(s: str) -> str:
        return shlex.quote(s)
    
    def remove(self, path: str, recursive: bool = False) -> str:
        flags = "-rf" if recursive else "-f"
        return f"rm {flags} {self.quote(path)}"
    
    def create_directory(self, path: str, mode: Optional[str] = None) -> str:
        cmd = f"mkdir -p {self.quote(path)}"
        if mode:
            cmd += f" && chmod {mode} {self.quote(path)}"
        return cmd


class PowerShellCommandBuilder(CommandBuilder):
    """PowerShell command builder for Windows."""
    
    @staticmethod
    def quote(s: str) -> str:
        # PowerShell single-quote escaping
        return "'" + s.replace("'", "''") + "'"
    
    def remove(self, path: str, recursive: bool = False) -> str:
        flags = "-Recurse -Force" if recursive else "-Force"
        return f"Remove-Item -LiteralPath {self.quote(path)} {flags}"
    
    def create_directory(self, path: str, mode: Optional[str] = None) -> str:
        return f"New-Item -ItemType Directory -Path {self.quote(path)} -Force"
```

---

## 8. TODO Items Found in Codebase

| File | Line | TODO | Priority |
|------|------|------|----------|
| [builtin_file.py](src/sansible/modules/builtin_file.py#L123) | 123 | Check/set mode if specified | Medium |
| [builtin_file.py](src/sansible/modules/builtin_file.py#L197) | 197 | Check/set mode | Medium |
| [builtin_copy.py](src/sansible/modules/builtin_copy.py#L134) | 134 | Implement directory copy | High |
| [cli/inventory.py](src/sansible/cli/inventory.py#L104) | 104 | Implement inventory parsing | Low (placeholder) |
| [cli/main.py](src/sansible/cli/main.py#L103) | 103 | Implement ad-hoc execution | Low (placeholder) |

---

## Conclusion

Sansible has a solid foundation with clean architecture and good async patterns. The main areas for improvement are:

1. **Reduce module boilerplate** through base class enhancements
2. **Decompose large classes** (especially `PlaybookRunner`)
3. **Improve error handling specificity**
4. **Increase test coverage** for core engine components
5. **Create shared abstractions** for Windows/Linux modules

Implementing the Phase 1 quick wins would provide immediate value with minimal risk, while the larger refactors in Phases 2-3 should be tackled incrementally with thorough testing.
