"""
Sansible Result Classes

Data structures for task, play, and playbook execution results.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import json


class TaskStatus(Enum):
    """Status of a task execution."""
    OK = "ok"
    CHANGED = "changed"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNREACHABLE = "unreachable"


@dataclass
class TaskResult:
    """Result of executing a single task on a single host."""
    
    host: str
    task_name: str
    status: TaskStatus
    changed: bool = False
    rc: int = 0
    stdout: str = ""
    stderr: str = ""
    msg: str = ""
    # Additional module-specific results
    results: Dict[str, Any] = field(default_factory=dict)
    # For loop results
    loop_results: Optional[List['TaskResult']] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        result = {
            "host": self.host,
            "task": self.task_name,
            "status": self.status.value,
            "changed": self.changed,
            "rc": self.rc,
        }
        if self.stdout:
            result["stdout"] = self.stdout
        if self.stderr:
            result["stderr"] = self.stderr
        if self.msg:
            result["msg"] = self.msg
        if self.results:
            result["results"] = self.results
        if self.loop_results:
            result["loop_results"] = [r.to_dict() for r in self.loop_results]
        return result
    
    @property
    def failed(self) -> bool:
        """Check if the task failed."""
        return self.status in (TaskStatus.FAILED, TaskStatus.UNREACHABLE)
    
    @property
    def ok(self) -> bool:
        """Check if the task succeeded (ok or changed)."""
        return self.status in (TaskStatus.OK, TaskStatus.CHANGED)


@dataclass
class HostStats:
    """Statistics for a single host across all tasks."""
    
    host: str
    ok: int = 0
    changed: int = 0
    failed: int = 0
    skipped: int = 0
    unreachable: int = 0
    
    def record(self, status: TaskStatus) -> None:
        """Record a task result status."""
        if status == TaskStatus.OK:
            self.ok += 1
        elif status == TaskStatus.CHANGED:
            self.changed += 1
        elif status == TaskStatus.FAILED:
            self.failed += 1
        elif status == TaskStatus.SKIPPED:
            self.skipped += 1
        elif status == TaskStatus.UNREACHABLE:
            self.unreachable += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "host": self.host,
            "ok": self.ok,
            "changed": self.changed,
            "failed": self.failed,
            "skipped": self.skipped,
            "unreachable": self.unreachable,
        }
    
    def merge(self, other: 'HostStats') -> None:
        """Merge another HostStats into this one."""
        self.ok += other.ok
        self.changed += other.changed
        self.failed += other.failed
        self.skipped += other.skipped
        self.unreachable += other.unreachable
    
    @property
    def has_failures(self) -> bool:
        """Check if host has any failures."""
        return self.failed > 0 or self.unreachable > 0


@dataclass
class PlayResult:
    """Result of executing a single play."""
    
    play_name: str
    hosts: List[str]
    task_results: List[TaskResult] = field(default_factory=list)
    host_stats: Dict[str, HostStats] = field(default_factory=dict)
    
    def add_result(self, result: TaskResult) -> None:
        """Add a task result."""
        self.task_results.append(result)
        
        if result.host not in self.host_stats:
            self.host_stats[result.host] = HostStats(result.host)
        self.host_stats[result.host].record(result.status)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "play": self.play_name,
            "hosts": self.hosts,
            "tasks": [r.to_dict() for r in self.task_results],
            "stats": {h: s.to_dict() for h, s in self.host_stats.items()},
        }
    
    @property
    def has_failures(self) -> bool:
        """Check if any host failed in this play."""
        return any(s.has_failures for s in self.host_stats.values())


@dataclass
class PlaybookResult:
    """Result of executing an entire playbook."""
    
    playbook_path: str
    play_results: List[PlayResult] = field(default_factory=list)
    
    def add_play_result(self, result: PlayResult) -> None:
        """Add a play result."""
        self.play_results.append(result)
    
    def get_final_stats(self) -> Dict[str, HostStats]:
        """Get aggregated stats for all hosts across all plays."""
        final_stats: Dict[str, HostStats] = {}
        
        for play_result in self.play_results:
            for host, stats in play_result.host_stats.items():
                if host not in final_stats:
                    final_stats[host] = HostStats(host)
                final_stats[host].ok += stats.ok
                final_stats[host].changed += stats.changed
                final_stats[host].failed += stats.failed
                final_stats[host].skipped += stats.skipped
                final_stats[host].unreachable += stats.unreachable
        
        return final_stats
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "playbook": self.playbook_path,
            "plays": [p.to_dict() for p in self.play_results],
            "stats": {h: s.to_dict() for h, s in self.get_final_stats().items()},
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    @property
    def success(self) -> bool:
        """Check if the entire playbook succeeded."""
        return not any(p.has_failures for p in self.play_results)
    
    @property
    def exit_code(self) -> int:
        """Get appropriate exit code."""
        return 0 if self.success else 2
