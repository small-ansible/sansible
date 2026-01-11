"""
Sansible Engine Module

Core execution engine for parsing and running playbooks.
"""

from sansible.engine.inventory import InventoryManager
from sansible.engine.playbook import PlaybookParser, Play, Task
from sansible.engine.templating import TemplateEngine
from sansible.engine.scheduler import Scheduler
from sansible.engine.results import TaskResult, PlayResult, PlaybookResult
from sansible.engine.errors import (
    SansibleError,
    ParseError,
    UnsupportedFeatureError,
    ConnectionError,
    ModuleError,
)

__all__ = [
    'InventoryManager',
    'PlaybookParser',
    'Play',
    'Task',
    'TemplateEngine',
    'Scheduler',
    'TaskResult',
    'PlayResult',
    'PlaybookResult',
    'SansibleError',
    'ParseError',
    'UnsupportedFeatureError',
    'ConnectionError',
    'ModuleError',
]
