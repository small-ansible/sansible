"""
Sansible Playbook Parser

Parses YAML playbooks into executable Play and Task objects.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from sansible.engine.errors import ParseError, UnsupportedFeatureError


# Pattern for Galaxy collection module names (namespace.collection.module)
GALAXY_MODULE_PATTERN = re.compile(r'^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$')


# Known module names and their aliases (FQCN -> short name)
MODULE_ALIASES = {
    'ansible.builtin.copy': 'copy',
    'ansible.builtin.command': 'command',
    'ansible.builtin.shell': 'shell',
    'ansible.builtin.raw': 'raw',
    'ansible.builtin.debug': 'debug',
    'ansible.builtin.set_fact': 'set_fact',
    'ansible.builtin.fail': 'fail',
    'ansible.builtin.assert': 'assert',
    'ansible.builtin.file': 'file',
    'ansible.builtin.template': 'template',
    'ansible.builtin.lineinfile': 'lineinfile',
    'ansible.builtin.stat': 'stat',
    'ansible.builtin.wait_for': 'wait_for',
    'ansible.builtin.pause': 'pause',
    'ansible.windows.win_copy': 'win_copy',
    'ansible.windows.win_command': 'win_command',
    'ansible.windows.win_shell': 'win_shell',
    'ansible.windows.win_file': 'win_file',
}

# Supported modules in v0.3
SUPPORTED_MODULES = {
    # Core modules
    'command', 'shell', 'raw', 'copy', 'file', 'template', 'debug',
    'set_fact', 'fail', 'assert', 'ping', 'setup', 'stat', 'lineinfile',
    'wait_for', 'fetch', 'find', 'service', 'user', 'group', 'group_by',
    'apt', 'yum', 'dnf', 'package', 'pip', 'git', 'uri', 'pause', 'meta',
    'add_host', 'include_vars', 'include_tasks', 'import_tasks',
    'include_role', 'import_role', 'get_url',
    # Extended modules
    'blockinfile', 'replace', 'slurp', 'tempfile', 'script', 'hostname',
    'cron', 'reboot', 'unarchive', 'systemd', 'systemd_service',
    'known_hosts', 'getent', 'wait_for_connection',
    # Windows modules
    'win_command', 'win_shell', 'win_copy', 'win_file', 'win_stat',
    'win_lineinfile', 'win_wait_for', 'win_service', 'win_ping',
    'win_reboot', 'win_user', 'win_group', 'win_template', 'win_hostname',
    'win_slurp', 'win_get_url',
}

# Task keys that are NOT module names
TASK_KEYWORDS = {
    'name', 'hosts', 'vars', 'vars_files', 'tasks', 'handlers', 'roles',
    'pre_tasks', 'post_tasks', 'gather_facts', 'become', 'become_user',
    'become_method', 'connection', 'environment', 'strategy', 'serial',
    'max_fail_percentage', 'any_errors_fatal', 'ignore_errors', 'ignore_unreachable',
    'module_defaults', 'collections', 'tags', 'when', 'register', 'loop',
    'with_items', 'with_list', 'with_dict', 'with_fileglob', 'with_sequence',
    'until', 'retries', 'delay', 'changed_when', 'failed_when', 'notify',
    'listen', 'delegate_to', 'delegate_facts', 'run_once', 'block', 'rescue',
    'always', 'args', 'async', 'poll', 'throttle', 'timeout', 'no_log',
    'diff', 'check_mode', 'local_action', 'action',
}

# Unsupported features that we should error on
UNSUPPORTED_TASK_KEYS = {
    'async', 'poll',  # Async
    'delegate_facts',  # Delegation facts (delegate_to is supported)
    'local_action',  # Local action
    'include',  # Old-style include (deprecated)
}


@dataclass
class Task:
    """Represents a single task in a playbook."""
    
    name: str
    module: str
    args: Dict[str, Any]
    register: Optional[str] = None
    when: Optional[str] = None
    loop: Optional[List[Any]] = None
    loop_var: str = "item"
    ignore_errors: bool = False
    changed_when: Optional[str] = None
    failed_when: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    become: Optional[bool] = None  # None = inherit from play
    become_user: Optional[str] = None
    become_method: Optional[str] = None
    notify: List[str] = field(default_factory=list)  # Handlers to notify
    listen: List[str] = field(default_factory=list)  # Handler triggers
    delegate_to: Optional[str] = None  # Delegate task to another host
    
    # Original line number for error reporting
    _line_number: Optional[int] = None
    
    # Block metadata (for rescue/always handling)
    _block_name: Optional[str] = None
    _is_rescue: bool = False
    _is_always: bool = False
    
    def __repr__(self) -> str:
        return f"Task(name={self.name!r}, module={self.module!r})"


@dataclass
class Block:
    """Represents a block of tasks with error handling."""
    
    name: str = ""
    block: List["Task"] = field(default_factory=list)
    rescue: List["Task"] = field(default_factory=list)
    always: List["Task"] = field(default_factory=list)
    when: Optional[str] = None
    become: Optional[bool] = None
    become_user: Optional[str] = None
    become_method: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def __repr__(self) -> str:
        return f"Block(name={self.name!r}, tasks={len(self.block)})"


@dataclass
class Play:
    """Represents a single play in a playbook."""
    
    name: str
    hosts: str
    tasks: List[Task] = field(default_factory=list)
    handlers: List[Task] = field(default_factory=list)  # Handler tasks
    vars: Dict[str, Any] = field(default_factory=dict)
    vars_files: List[str] = field(default_factory=list)
    gather_facts: bool = False  # Default to False in Sansible
    connection: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    become: bool = False  # Privilege escalation
    become_user: str = "root"
    become_method: str = "sudo"
    
    # Original line number for error reporting
    _line_number: Optional[int] = None
    
    def __repr__(self) -> str:
        return f"Play(name={self.name!r}, hosts={self.hosts!r}, tasks={len(self.tasks)})"


class PlaybookParser:
    """
    Parse YAML playbooks into Play and Task objects.
    
    Validates against supported subset and raises errors for unsupported features.
    """
    
    def __init__(self, playbook_path: Union[str, Path]):
        self.playbook_path = Path(playbook_path)
        self.plays: List[Play] = []
        self._base_dir = self.playbook_path.parent
    
    def parse(self) -> List[Play]:
        """
        Parse the playbook file.
        
        Returns:
            List of Play objects
            
        Raises:
            ParseError: If the playbook has syntax errors
            UnsupportedFeatureError: If playbook uses unsupported features
        """
        if not self.playbook_path.exists():
            raise ParseError(
                f"Playbook not found: {self.playbook_path}",
                file_path=str(self.playbook_path)
            )
        
        content = self.playbook_path.read_text(encoding='utf-8')
        
        try:
            # Use safe_load_all for multi-document YAML (though playbooks are usually single-doc)
            documents = list(yaml.safe_load_all(content))
        except yaml.YAMLError as e:
            raise ParseError(
                f"YAML syntax error: {e}",
                file_path=str(self.playbook_path)
            )
        
        # Flatten all documents (usually just one)
        all_plays = []
        for doc in documents:
            if doc is None:
                continue
            if isinstance(doc, list):
                all_plays.extend(doc)
            elif isinstance(doc, dict):
                all_plays.append(doc)
        
        for play_data in all_plays:
            if isinstance(play_data, dict):
                play = self._parse_play(play_data)
                self.plays.append(play)
        
        return self.plays
    
    def _parse_play(self, data: Dict[str, Any]) -> Play:
        """Parse a single play from YAML data."""
        # Check for unsupported play-level features
        for key in UNSUPPORTED_TASK_KEYS:
            if key in data:
                raise UnsupportedFeatureError(
                    f"'{key}' in plays",
                    suggestion=f"Remove '{key}' or use standard Ansible for this playbook"
                )
        
        # Required: hosts
        if 'hosts' not in data:
            raise ParseError(
                "Play missing required 'hosts' field",
                file_path=str(self.playbook_path)
            )
        
        # Parse play attributes
        play = Play(
            name=data.get('name', 'Unnamed play'),
            hosts=data['hosts'],
            gather_facts=data.get('gather_facts', False),
            connection=data.get('connection'),
            environment=data.get('environment', {}),
            tags=self._ensure_list(data.get('tags', [])),
        )
        
        # Parse vars
        if 'vars' in data:
            if isinstance(data['vars'], dict):
                play.vars = data['vars']
            else:
                raise ParseError(
                    f"'vars' must be a dictionary, got {type(data['vars']).__name__}",
                    file_path=str(self.playbook_path)
                )
        
        # Parse vars_files
        if 'vars_files' in data:
            play.vars_files = self._ensure_list(data['vars_files'])
            # Load vars_files immediately
            for vars_file in play.vars_files:
                vars_path = self._base_dir / vars_file
                if vars_path.exists():
                    vars_data = yaml.safe_load(vars_path.read_text(encoding='utf-8')) or {}
                    if isinstance(vars_data, dict):
                        play.vars.update(vars_data)
                else:
                    raise ParseError(
                        f"vars_file not found: {vars_file}",
                        file_path=str(self.playbook_path)
                    )
        
        # Parse pre_tasks (run before roles)
        pre_tasks: List[Task] = []
        if 'pre_tasks' in data:
            for task_data in data['pre_tasks']:
                if isinstance(task_data, dict):
                    parsed = self._parse_task_or_block(task_data)
                    if isinstance(parsed, list):
                        pre_tasks.extend(parsed)
                    else:
                        pre_tasks.append(parsed)
        
        # Parse roles and expand to tasks
        role_tasks: List[Task] = []
        if 'roles' in data:
            roles = self._ensure_list(data['roles'])
            for role_entry in roles:
                tasks = self._load_role(role_entry, play.vars)
                role_tasks.extend(tasks)
        
        # Parse tasks
        regular_tasks: List[Task] = []
        if 'tasks' in data:
            for task_data in data['tasks']:
                if isinstance(task_data, dict):
                    parsed = self._parse_task_or_block(task_data)
                    if isinstance(parsed, list):
                        regular_tasks.extend(parsed)
                    else:
                        regular_tasks.append(parsed)
        
        # Parse post_tasks (run after tasks)
        post_tasks: List[Task] = []
        if 'post_tasks' in data:
            for task_data in data['post_tasks']:
                if isinstance(task_data, dict):
                    parsed = self._parse_task_or_block(task_data)
                    if isinstance(parsed, list):
                        post_tasks.extend(parsed)
                    else:
                        post_tasks.append(parsed)
        
        # Combine in correct order: pre_tasks -> roles -> tasks -> post_tasks
        play.tasks = pre_tasks + role_tasks + regular_tasks + post_tasks
        
        # Parse handlers
        if 'handlers' in data:
            for handler_data in data['handlers']:
                if isinstance(handler_data, dict):
                    handler = self._parse_task(handler_data)
                    # Parse listen field for handlers
                    if 'listen' in handler_data:
                        listen = handler_data['listen']
                        if isinstance(listen, str):
                            handler.listen = [listen]
                        elif isinstance(listen, list):
                            handler.listen = listen
                    play.handlers.append(handler)
        
        return play
    
    def _load_role(self, role_entry: Any, play_vars: Dict[str, Any]) -> List[Task]:
        """
        Load tasks from a role.
        
        Args:
            role_entry: Either a string (role name) or dict with role, vars, etc.
            play_vars: Variables from the play level
            
        Returns:
            List of Task objects from the role
        """
        # Parse role entry
        if isinstance(role_entry, str):
            role_name = role_entry
            role_vars: Dict[str, Any] = {}
            role_tags: List[str] = []
            role_when: Optional[str] = None
        elif isinstance(role_entry, dict):
            role_name = role_entry.get('role') or role_entry.get('name')
            if not role_name:
                raise ParseError(
                    "Role entry must have 'role' or 'name' key",
                    file_path=str(self.playbook_path)
                )
            role_vars = {k: v for k, v in role_entry.items() 
                        if k not in ('role', 'name', 'tags', 'when')}
            role_tags = self._ensure_list(role_entry.get('tags', []))
            role_when = role_entry.get('when')
        else:
            raise ParseError(
                f"Invalid role entry type: {type(role_entry).__name__}",
                file_path=str(self.playbook_path)
            )
        
        # Find the role directory
        role_path = self._find_role_path(role_name)
        if not role_path:
            raise ParseError(
                f"Role not found: {role_name}",
                file_path=str(self.playbook_path)
            )
        
        # Load role defaults (lowest priority)
        defaults_file = role_path / "defaults" / "main.yml"
        if defaults_file.exists():
            defaults = yaml.safe_load(defaults_file.read_text(encoding='utf-8')) or {}
            if isinstance(defaults, dict):
                # Defaults have lower priority than play vars
                role_vars = {**defaults, **role_vars}
        
        # Load role vars (higher priority than defaults, lower than play vars)
        vars_file = role_path / "vars" / "main.yml"
        if vars_file.exists():
            role_specific_vars = yaml.safe_load(vars_file.read_text(encoding='utf-8')) or {}
            if isinstance(role_specific_vars, dict):
                role_vars.update(role_specific_vars)
        
        # Load tasks
        tasks_file = role_path / "tasks" / "main.yml"
        if not tasks_file.exists():
            raise ParseError(
                f"Role tasks file not found: {tasks_file}",
                file_path=str(self.playbook_path)
            )
        
        tasks_data = yaml.safe_load(tasks_file.read_text(encoding='utf-8')) or []
        if not isinstance(tasks_data, list):
            raise ParseError(
                f"Role tasks must be a list: {tasks_file}",
                file_path=str(self.playbook_path)
            )
        
        tasks: List[Task] = []
        for task_data in tasks_data:
            if isinstance(task_data, dict):
                task = self._parse_task(task_data)
                
                # Apply role-level tags
                if role_tags:
                    task.tags = list(set(task.tags + role_tags))
                
                # Apply role-level when condition
                if role_when:
                    if task.when:
                        task.when = f"({role_when}) and ({task.when})"
                    else:
                        task.when = role_when
                
                # Store role vars for later use (will be merged in runner)
                if not hasattr(task, '_role_vars'):
                    task._role_vars = {}  # type: ignore
                task._role_vars.update(role_vars)  # type: ignore
                
                tasks.append(task)
        
        return tasks
    
    def _find_role_path(self, role_name: str) -> Optional[Path]:
        """
        Find the path to a role.
        
        Searches in:
        1. ./roles/<role_name>
        2. <playbook_dir>/roles/<role_name>
        
        Returns:
            Path to role directory or None if not found
        """
        search_paths = [
            self._base_dir / "roles" / role_name,
            Path.cwd() / "roles" / role_name,
        ]
        
        for path in search_paths:
            if path.is_dir():
                return path
        
        return None
    
    def _parse_task_or_block(self, data: Dict[str, Any]) -> "Task | List[Task]":
        """Parse a task or block, returning task(s)."""
        if 'block' in data:
            return self._parse_block(data)
        if 'include_tasks' in data or 'import_tasks' in data:
            return self._parse_include_tasks(data)
        if 'include_role' in data or 'import_role' in data:
            return self._parse_include_role(data)
        return self._parse_task(data)
    
    def _parse_include_tasks(self, data: Dict[str, Any]) -> List[Task]:
        """
        Parse include_tasks or import_tasks directive.
        
        Both are handled the same way at parse time (static inclusion).
        """
        # Get the tasks file path
        tasks_file = data.get('include_tasks') or data.get('import_tasks')
        if isinstance(tasks_file, dict):
            tasks_file = tasks_file.get('file')
        
        if not tasks_file:
            raise ParseError(
                "include_tasks/import_tasks requires a file path",
                file_path=str(self.playbook_path)
            )
        
        # Resolve relative to playbook directory
        tasks_path = self._base_dir / tasks_file
        if not tasks_path.exists():
            raise ParseError(
                f"Tasks file not found: {tasks_file}",
                file_path=str(self.playbook_path)
            )
        
        # Load and parse the tasks file
        tasks_data = yaml.safe_load(tasks_path.read_text(encoding='utf-8')) or []
        if not isinstance(tasks_data, list):
            raise ParseError(
                f"Tasks file must contain a list: {tasks_file}",
                file_path=str(self.playbook_path)
            )
        
        # Parse each task
        tasks: List[Task] = []
        include_when = data.get('when')
        include_tags = self._ensure_list(data.get('tags', []))
        
        for task_data in tasks_data:
            if isinstance(task_data, dict):
                parsed = self._parse_task_or_block(task_data)
                parsed_list = parsed if isinstance(parsed, list) else [parsed]
                for task in parsed_list:
                    # Apply include-level when condition
                    if include_when:
                        if task.when:
                            task.when = f"({include_when}) and ({task.when})"
                        else:
                            task.when = include_when
                    # Apply include-level tags
                    if include_tags:
                        task.tags = list(set(task.tags + include_tags))
                    tasks.append(task)
        
        return tasks
    
    def _parse_include_role(self, data: Dict[str, Any]) -> List[Task]:
        """
        Parse include_role or import_role directive.
        """
        role_data = data.get('include_role') or data.get('import_role')
        
        if isinstance(role_data, str):
            role_name = role_data
            role_vars: Dict[str, Any] = {}
        elif isinstance(role_data, dict):
            role_name = role_data.get('name')
            role_vars = {k: v for k, v in role_data.items() if k != 'name'}
        else:
            raise ParseError(
                "include_role/import_role requires a role name",
                file_path=str(self.playbook_path)
            )
        
        if not role_name:
            raise ParseError(
                "include_role/import_role requires 'name' parameter",
                file_path=str(self.playbook_path)
            )
        
        # Get additional vars from the task level
        if 'vars' in data:
            role_vars.update(data['vars'])
        
        include_when = data.get('when')
        include_tags = self._ensure_list(data.get('tags', []))
        
        # Load the role tasks
        tasks = self._load_role(
            {'role': role_name, 'when': include_when, 'tags': include_tags, **role_vars},
            {}
        )
        
        return tasks
    
    def _parse_block(self, data: Dict[str, Any]) -> List[Task]:
        """
        Parse a block into a list of tasks.
        
        Blocks are expanded into tasks with special metadata for
        rescue/always handling at execution time.
        """
        block_name = data.get('name', 'block')
        block_when = data.get('when')
        block_become = data.get('become')
        block_become_user = data.get('become_user')
        block_tags = data.get('tags', [])
        
        tasks: List[Task] = []
        
        def apply_block_props(task: Task) -> Task:
            """Apply block properties to a task."""
            if block_when and not task.when:
                task.when = block_when
            if block_become is not None and task.become is None:
                task.become = block_become
            if block_become_user and not task.become_user:
                task.become_user = block_become_user
            if block_tags:
                task.tags = list(set(task.tags + block_tags))
            task._block_name = block_name
            return task
        
        # Parse main block tasks (may include nested blocks)
        block_tasks_data = data.get('block', [])
        for task_data in block_tasks_data:
            if isinstance(task_data, dict):
                parsed = self._parse_task_or_block(task_data)
                if isinstance(parsed, list):
                    for t in parsed:
                        tasks.append(apply_block_props(t))
                else:
                    tasks.append(apply_block_props(parsed))
        
        # Parse rescue tasks (run on block failure)
        rescue_data = data.get('rescue', [])
        for task_data in rescue_data:
            if isinstance(task_data, dict):
                parsed = self._parse_task_or_block(task_data)
                if isinstance(parsed, list):
                    for t in parsed:
                        t._is_rescue = True
                        tasks.append(apply_block_props(t))
                else:
                    parsed._is_rescue = True
                    tasks.append(apply_block_props(parsed))
        
        # Parse always tasks (always run)
        always_data = data.get('always', [])
        for task_data in always_data:
            if isinstance(task_data, dict):
                parsed = self._parse_task_or_block(task_data)
                if isinstance(parsed, list):
                    for t in parsed:
                        t._is_always = True
                        tasks.append(apply_block_props(t))
                else:
                    parsed._is_always = True
                    tasks.append(apply_block_props(parsed))
        
        return tasks
        
        return tasks

    def _parse_task(self, data: Dict[str, Any]) -> Task:
        """Parse a single task from YAML data."""
        # Check for unsupported task-level features
        for key in UNSUPPORTED_TASK_KEYS:
            if key in data:
                raise UnsupportedFeatureError(
                    f"'{key}' in tasks",
                    suggestion=f"Remove '{key}' or use standard Ansible for this playbook"
                )
        
        # Find the module and its args
        module_name = None
        module_args: Any = None
        
        for key, value in data.items():
            if key in TASK_KEYWORDS:
                continue
            
            # This key is likely the module name
            # Check if it's a known module or FQCN
            normalized = MODULE_ALIASES.get(key, key)
            
            if normalized in SUPPORTED_MODULES:
                module_name = normalized
                module_args = value
                break
            elif GALAXY_MODULE_PATTERN.match(key):
                # Galaxy module (namespace.collection.module format)
                module_name = key
                module_args = value
                break
            elif key not in TASK_KEYWORDS:
                # Unknown module - check if it looks like a module call
                if value is not None or '.' in key:
                    raise UnsupportedFeatureError(
                        f"Module '{key}' is not supported",
                        suggestion="Only copy, command, shell, raw, debug, set_fact, fail, assert, and win_* modules are supported, or use Galaxy modules (namespace.collection.module format)"
                    )
        
        if module_name is None:
            raise ParseError(
                f"Task has no recognized module: {list(data.keys())}",
                file_path=str(self.playbook_path)
            )
        
        # Parse module args
        args = self._normalize_args(module_name, module_args)
        
        # Parse loop/with_items
        loop = None
        loop_var = "item"
        if 'loop' in data:
            loop = data['loop']
        elif 'with_items' in data:
            loop = data['with_items']
        elif 'with_list' in data:
            loop = data['with_list']
        
        if 'loop_control' in data and isinstance(data['loop_control'], dict):
            loop_var = data['loop_control'].get('loop_var', 'item')
        
        # Parse when condition
        when = data.get('when')
        if when is not None and not isinstance(when, str):
            # Handle list of conditions (AND them together)
            if isinstance(when, list):
                when = ' and '.join(str(w) for w in when)
            else:
                when = str(when)
        
        # Parse notify
        notify = data.get('notify', [])
        if isinstance(notify, str):
            notify = [notify]
        elif not isinstance(notify, list):
            notify = []
        
        # Parse delegate_to
        delegate_to = data.get('delegate_to')
        
        return Task(
            name=data.get('name', f'{module_name} task'),
            module=module_name,
            args=args,
            register=data.get('register'),
            when=when,
            loop=loop,
            loop_var=loop_var,
            ignore_errors=data.get('ignore_errors', False),
            changed_when=data.get('changed_when'),
            failed_when=data.get('failed_when'),
            environment=data.get('environment', {}),
            tags=self._ensure_list(data.get('tags', [])),
            notify=notify,
            delegate_to=delegate_to,
        )
    
    def _normalize_args(self, module_name: str, args: Any) -> Dict[str, Any]:
        """Normalize module arguments to a dictionary."""
        if args is None:
            return {}
        
        if isinstance(args, dict):
            return args
        
        if isinstance(args, str):
            # Handle inline args: "src=foo dest=bar"
            parsed = {}
            # Simple key=value parsing (doesn't handle all edge cases)
            pattern = re.compile(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))')
            for match in pattern.finditer(args):
                key = match.group(1)
                value = match.group(2) or match.group(3) or match.group(4)
                parsed[key] = value
            
            # If no key=value pairs found, treat as free-form (for shell/command)
            if not parsed and module_name in ('command', 'shell', 'raw', 'win_command', 'win_shell'):
                parsed['_raw_params'] = args
            
            return parsed
        
        return {'_raw_params': str(args)}
    
    def _ensure_list(self, value: Any) -> List[Any]:
        """Ensure a value is a list."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]
