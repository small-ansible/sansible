# Sansible Architecture

This document describes the internal architecture of Sansible.

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI (cli.py)                         │
│  - Parse arguments                                           │
│  - Load inventory and playbook                               │
│  - Execute and report results                                │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Engine Layer                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Inventory  │  │  Playbook   │  │     Templating      │  │
│  │   Manager   │  │   Parser    │  │      Engine         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│                 ┌─────────────────┐                         │
│                 │    Scheduler    │                         │
│                 │  (asyncio-based)│                         │
│                 └────────┬────────┘                         │
└──────────────────────────┼──────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │   Local    │  │    SSH     │  │   WinRM    │
    │ Connection │  │ Connection │  │ Connection │
    └────────────┘  └────────────┘  └────────────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │      Module Layer       │
              │  ┌────────┐ ┌────────┐  │
              │  │ copy   │ │ shell  │  │
              │  ├────────┤ ├────────┤  │
              │  │command │ │  raw   │  │
              │  ├────────┤ ├────────┤  │
              │  │ debug  │ │win_*   │  │
              │  └────────┘ └────────┘  │
              └─────────────────────────┘
```

## Component Details

### CLI (`cli.py`)

The command-line interface is the main entry point:

```python
san run -i inventory.ini playbook.yml --forks 5
```

Responsibilities:
- Parse command-line arguments
- Load and parse inventory
- Load and parse playbook
- Create scheduler with connection factory
- Execute playbook
- Format and display results

### Engine Layer

#### Inventory Manager (`engine/inventory.py`)

Parses inventory files and manages host/group data:

- INI format parser (standard Ansible format)
- YAML format parser
- Host pattern matching (`all`, `group`, `host1,host2`)
- Variable merging (group_vars, host_vars)
- Range expansion (`web[01:10].example.com`)

Key classes:
- `InventoryManager`: Main entry point
- `Host`: Single host representation
- `Group`: Group with hosts and children

#### Playbook Parser (`engine/playbook.py`)

Parses YAML playbooks into executable structures:

- YAML parsing with `yaml.safe_load_all`
- Module name normalization (FQCN → short name)
- Task validation
- Unsupported feature detection

Key classes:
- `PlaybookParser`: Parse playbook file
- `Play`: Single play representation
- `Task`: Single task representation

#### Templating Engine (`engine/templating.py`)

Jinja2-based variable rendering:

- Variable interpolation (`{{ var }}`)
- Filter support (minimal set)
- `when` condition evaluation
- Recursive template rendering

Supported filters:
- `default`, `lower`, `upper`, `replace`
- `to_json`, `to_yaml`, `trim`
- `join`, `first`, `last`
- `basename`, `dirname`, `regex_replace`

#### Scheduler (`engine/scheduler.py`)

Async execution engine:

```python
async def run_playbook(plays, hosts, module_runner):
    for play in plays:
        for task in play.tasks:
            # Run task on all hosts in parallel (bounded by forks)
            results = await run_task_on_hosts(task, hosts)
```

Key features:
- Uses `asyncio` for concurrency
- Semaphore-based parallelism (respects `--forks`)
- Per-host context management
- Linear strategy (task-by-task across hosts)

### Connection Layer

#### Base Connection (`connections/base.py`)

Abstract interface for all connections:

```python
class Connection(ABC):
    async def connect(self) -> None
    async def close(self) -> None
    async def run(command, shell, timeout, cwd) -> RunResult
    async def put(local_path, remote_path, mode) -> None
    async def get(remote_path, local_path) -> None
    async def mkdir(remote_path, mode) -> None
    async def stat(remote_path) -> Optional[dict]
```

#### Local Connection (`connections/local.py`)

Execute on the control node:
- Uses `asyncio.create_subprocess_shell/exec`
- File operations via `shutil`
- No network overhead

#### SSH Connection (`connections/ssh_asyncssh.py`)

SSH via `asyncssh`:
- Native async SSH client
- SFTP for file transfers
- Key and password authentication
- Configurable known_hosts handling

#### WinRM Connection (`connections/winrm_psrp.py`)

Windows Remote Management via `pypsrp`:
- PowerShell Remoting Protocol
- NTLM/Kerberos authentication
- Chunked base64 file transfer (avoids WinRM size limits)

### Module Layer

#### Base Module (`modules/base.py`)

Module interface and registry:

```python
class Module(ABC):
    name: str
    required_args: List[str]
    optional_args: Dict[str, Any]
    
    async def run(self) -> ModuleResult
```

Registry pattern:
```python
@register_module
class ShellModule(Module):
    name = "shell"
    ...
```

#### Built-in Modules

| Module | Purpose |
|--------|---------|
| `command` | Execute without shell |
| `shell` | Execute with shell |
| `raw` | Direct execution |
| `copy` | File transfer |
| `file` | Manage files/directories/links |
| `template` | Jinja2 template rendering |
| `debug` | Print messages |
| `set_fact` | Set variables |
| `fail` | Explicit failure |
| `assert` | Condition check |
| `win_command` | Windows cmd.exe |
| `win_shell` | Windows PowerShell |
| `win_copy` | Windows file copy |
| `win_file` | Windows file/directory management |

### Roles Support

Sansible supports Ansible roles with the following structure:

```
roles/
  my_role/
    tasks/
      main.yml      # Required: task list
    defaults/
      main.yml      # Optional: default variables (lowest priority)
    vars/
      main.yml      # Optional: role variables (higher priority)
```

Role resolution order:
1. `roles/` directory relative to playbook
2. `./roles/` in current directory

Role features supported:
- `tasks/main.yml` inlining
- `defaults/main.yml` variable loading
- `vars/main.yml` variable loading
- Role-level `tags` and `when` conditions

## Data Flow

### Execution Sequence

1. **Parse Phase**
   ```
   CLI → InventoryManager.parse() → hosts, groups
   CLI → PlaybookParser.parse() → plays, tasks
   ```

2. **Setup Phase**
   ```
   Scheduler → create_connection_factory()
   Scheduler → create HostContext for each host
   Scheduler → establish connections (parallel)
   ```

3. **Execution Phase** (per play)
   ```
   For each task:
     For each host (parallel, bounded by forks):
       TemplateEngine → render task args
       evaluate 'when' condition
       Module.run() → ModuleResult
       record result, update registered vars
   ```

4. **Cleanup Phase**
   ```
   Scheduler → close connections
   CLI → format results
   CLI → print recap
   ```

### Variable Precedence

Lower number = lower priority (overridden by higher):

1. Group vars from inventory
2. `group_vars/` files
3. Host vars from inventory
4. `host_vars/` files
5. Play `vars`
6. Play `vars_files`
7. Extra vars (`-e`)
8. `set_fact` during execution
9. `register` results

## Error Handling

### Error Types

| Error | Exit Code | Description |
|-------|-----------|-------------|
| `ParseError` | 3 | Invalid YAML/INI |
| `UnsupportedFeatureError` | 4 | Unsupported Ansible feature |
| `ConnectionError` | 2 | Cannot connect to host |
| `ModuleError` | 2 | Module execution failed |

### Fail Behavior

- **Host failure**: Skip remaining tasks on that host
- **All hosts failed**: Stop playbook execution
- **`ignore_errors: true`**: Continue despite failure

## Performance Considerations

### Parallelism

- Async scheduler with semaphore (`--forks N`)
- Per-task parallelism (all hosts simultaneously)
- Connection pooling per host

### Memory

- Streaming file transfers (chunked)
- Lazy loading of vars files
- No full playbook AST caching

### Network

- Persistent SSH connections
- WinRM connection reuse
- Minimal round-trips per task

## Extension Points

### Adding Modules

1. Create `modules/my_module.py`
2. Subclass `Module`
3. Implement `run()` method
4. Decorate with `@register_module`

```python
from sansible.modules.base import Module, ModuleResult, register_module

@register_module
class MyModule(Module):
    name = "my_module"
    required_args = ["param1"]
    
    async def run(self) -> ModuleResult:
        value = self.args["param1"]
        result = await self.connection.run(f"echo {value}")
        return ModuleResult(
            changed=True,
            stdout=result.stdout,
        )
```

### Adding Connections

1. Create `connections/my_conn.py`
2. Subclass `Connection`
3. Implement all abstract methods
4. Register in `create_connection_factory()`
