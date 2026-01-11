"""
Sansible Compatibility Scanner

Scans Ansible playbooks and roles to determine module usage and compatibility
with Sansible's supported subset.
"""

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml


# Known module FQCNs and their short names
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
    'ansible.builtin.include_tasks': 'include_tasks',
    'ansible.builtin.import_tasks': 'import_tasks',
    'ansible.builtin.include_role': 'include_role',
    'ansible.builtin.import_role': 'import_role',
    'ansible.builtin.setup': 'setup',
    'ansible.builtin.gather_facts': 'gather_facts',
    'ansible.builtin.meta': 'meta',
    'ansible.builtin.package': 'package',
    'ansible.builtin.service': 'service',
    'ansible.builtin.user': 'user',
    'ansible.builtin.group': 'group',
    'ansible.builtin.apt': 'apt',
    'ansible.builtin.yum': 'yum',
    'ansible.builtin.dnf': 'dnf',
    'ansible.builtin.pip': 'pip',
    'ansible.builtin.git': 'git',
    'ansible.builtin.uri': 'uri',
    'ansible.builtin.get_url': 'get_url',
    'ansible.builtin.fetch': 'fetch',
    'ansible.builtin.unarchive': 'unarchive',
    'ansible.builtin.archive': 'archive',
    'ansible.builtin.cron': 'cron',
    'ansible.builtin.hostname': 'hostname',
    'ansible.builtin.reboot': 'reboot',
    'ansible.windows.win_copy': 'win_copy',
    'ansible.windows.win_command': 'win_command',
    'ansible.windows.win_shell': 'win_shell',
    'ansible.windows.win_file': 'win_file',
    'ansible.windows.win_template': 'win_template',
    'ansible.windows.win_stat': 'win_stat',
    'ansible.windows.win_service': 'win_service',
    'ansible.windows.win_package': 'win_package',
    'ansible.windows.win_reboot': 'win_reboot',
    'ansible.windows.win_user': 'win_user',
    'ansible.windows.win_group': 'win_group',
    'ansible.windows.win_feature': 'win_feature',
    'ansible.windows.win_firewall_rule': 'win_firewall_rule',
    'ansible.windows.win_scheduled_task': 'win_scheduled_task',
    'ansible.windows.win_environment': 'win_environment',
    'ansible.windows.win_registry': 'win_registry',
    'ansible.windows.win_dsc': 'win_dsc',
}

# Task keywords that are NOT module names
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

# Modules supported by Sansible v0.1
SUPPORTED_MODULES = {
    'copy', 'command', 'shell', 'raw', 'debug', 'set_fact', 'fail', 'assert',
    'file', 'template',
    'win_copy', 'win_command', 'win_shell', 'win_file',
}


@dataclass
class ScanResult:
    """Result of scanning a repository."""
    
    repo_path: str
    files_scanned: int = 0
    playbooks_found: int = 0
    roles_found: int = 0
    
    # Module usage
    modules_used: Counter = field(default_factory=Counter)
    modules_by_file: Dict[str, List[str]] = field(default_factory=dict)
    
    # Variables used
    vars_used: Set[str] = field(default_factory=set)
    
    # Features used
    features_used: Set[str] = field(default_factory=set)
    
    # Connection types
    connections_used: Set[str] = field(default_factory=set)
    
    # Errors encountered
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "repo_path": self.repo_path,
            "summary": {
                "files_scanned": self.files_scanned,
                "playbooks_found": self.playbooks_found,
                "roles_found": self.roles_found,
                "unique_modules": len(self.modules_used),
                "total_module_calls": sum(self.modules_used.values()),
            },
            "modules": {
                "usage_count": dict(self.modules_used.most_common()),
                "supported": [m for m in self.modules_used if m in SUPPORTED_MODULES],
                "unsupported": [m for m in self.modules_used if m not in SUPPORTED_MODULES],
                "by_file": self.modules_by_file,
            },
            "features": list(self.features_used),
            "connections": list(self.connections_used),
            "variables": list(self.vars_used)[:100],  # Limit for readability
            "errors": self.errors,
        }
    
    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            f"# Sansible Compatibility Scan",
            f"",
            f"**Repository:** `{self.repo_path}`",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Files scanned | {self.files_scanned} |",
            f"| Playbooks found | {self.playbooks_found} |",
            f"| Roles found | {self.roles_found} |",
            f"| Unique modules | {len(self.modules_used)} |",
            f"| Total module calls | {sum(self.modules_used.values())} |",
            f"",
            f"## Module Usage",
            f"",
            f"### Supported Modules (✅)",
            f"",
        ]
        
        supported = [(m, c) for m, c in self.modules_used.most_common() 
                     if m in SUPPORTED_MODULES]
        if supported:
            lines.append("| Module | Count |")
            lines.append("|--------|-------|")
            for mod, count in supported:
                lines.append(f"| `{mod}` | {count} |")
        else:
            lines.append("*No supported modules found.*")
        
        lines.extend([
            f"",
            f"### Unsupported Modules (❌)",
            f"",
        ])
        
        unsupported = [(m, c) for m, c in self.modules_used.most_common() 
                       if m not in SUPPORTED_MODULES]
        if unsupported:
            lines.append("| Module | Count |")
            lines.append("|--------|-------|")
            for mod, count in unsupported:
                lines.append(f"| `{mod}` | {count} |")
        else:
            lines.append("*All modules are supported!*")
        
        lines.extend([
            f"",
            f"## Connection Types",
            f"",
        ])
        
        if self.connections_used:
            for conn in sorted(self.connections_used):
                status = "✅" if conn in ('local', 'ssh', 'winrm') else "❌"
                lines.append(f"- `{conn}` {status}")
        else:
            lines.append("*No explicit connection types found.*")
        
        lines.extend([
            f"",
            f"## Features Used",
            f"",
        ])
        
        feature_status = {
            'roles': '✅',
            'pre_tasks': '✅',
            'post_tasks': '✅',
            'vars': '✅',
            'vars_files': '✅',
            'loop': '✅',
            'with_items': '✅',
            'when': '✅',
            'register': '✅',
            'ignore_errors': '✅',
            'tags': '✅',
            'handlers': '❌',
            'become': '❌',
            'block': '❌',
            'delegate_to': '❌',
            'gather_facts': '⚠️ (not implemented)',
        }
        
        if self.features_used:
            for feat in sorted(self.features_used):
                status = feature_status.get(feat, '❓')
                lines.append(f"- `{feat}` {status}")
        else:
            lines.append("*No special features detected.*")
        
        if self.errors:
            lines.extend([
                f"",
                f"## Errors",
                f"",
            ])
            for err in self.errors[:20]:  # Limit errors shown
                lines.append(f"- {err}")
        
        lines.extend([
            f"",
            f"---",
            f"",
            f"*Generated by Sansible Compatibility Scanner*",
        ])
        
        return "\n".join(lines)


class CompatibilityScanner:
    """Scan Ansible repositories for module usage and compatibility."""
    
    def __init__(self, repo_path: str, verbose: bool = False):
        self.repo_path = Path(repo_path).resolve()
        self.verbose = verbose
        self.result = ScanResult(repo_path=str(self.repo_path))
    
    def scan(self) -> ScanResult:
        """Scan the repository."""
        if not self.repo_path.is_dir():
            self.result.errors.append(f"Not a directory: {self.repo_path}")
            return self.result
        
        # Find all YAML files
        yaml_files = list(self.repo_path.rglob("*.yml")) + list(self.repo_path.rglob("*.yaml"))
        
        for yaml_file in yaml_files:
            # Skip hidden files and common non-playbook paths
            rel_path = yaml_file.relative_to(self.repo_path)
            if any(part.startswith('.') for part in rel_path.parts):
                continue
            if any(part in ('molecule', '.github', 'test', 'tests', 'meta') 
                   for part in rel_path.parts):
                continue
            
            self._scan_file(yaml_file)
        
        # Count roles
        roles_dir = self.repo_path / "roles"
        if roles_dir.is_dir():
            self.result.roles_found = sum(1 for d in roles_dir.iterdir() 
                                           if d.is_dir() and not d.name.startswith('.'))
        
        return self.result
    
    def _scan_file(self, file_path: Path) -> None:
        """Scan a single YAML file."""
        self.result.files_scanned += 1
        rel_path = str(file_path.relative_to(self.repo_path))
        
        try:
            content = file_path.read_text(encoding='utf-8')
            data = yaml.safe_load(content)
        except Exception as e:
            self.result.errors.append(f"{rel_path}: {e}")
            return
        
        if data is None:
            return
        
        # Check if this looks like a playbook
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict) and ('hosts' in first or 'tasks' in first):
                self.result.playbooks_found += 1
        
        # Extract modules and features
        modules = self._extract_modules(data, rel_path)
        if modules:
            self.result.modules_by_file[rel_path] = modules
            for mod in modules:
                self.result.modules_used[mod] += 1
        
        # Extract features
        self._extract_features(data)
        
        # Extract variables
        self._extract_variables(content)
    
    def _extract_modules(self, data: Any, file_path: str) -> List[str]:
        """Extract module names from YAML data."""
        modules: List[str] = []
        
        if isinstance(data, dict):
            # Check for module calls in task
            for key in data:
                if key not in TASK_KEYWORDS:
                    # Normalize FQCN
                    normalized = MODULE_ALIASES.get(key, key)
                    # Skip if it's clearly not a module
                    if not key.startswith('_') and '/' not in key:
                        modules.append(normalized)
            
            # Recurse into nested structures
            for value in data.values():
                modules.extend(self._extract_modules(value, file_path))
                
        elif isinstance(data, list):
            for item in data:
                modules.extend(self._extract_modules(item, file_path))
        
        return modules
    
    def _extract_features(self, data: Any) -> None:
        """Extract feature usage from YAML data."""
        if isinstance(data, dict):
            features = {'roles', 'pre_tasks', 'post_tasks', 'handlers', 
                       'become', 'block', 'delegate_to', 'gather_facts',
                       'loop', 'with_items', 'when', 'register', 'tags',
                       'ignore_errors', 'vars', 'vars_files', 'notify'}
            
            for key in data:
                if key in features:
                    self.result.features_used.add(key)
                
                # Check for connection type
                if key == 'connection':
                    self.result.connections_used.add(str(data[key]))
                elif key == 'ansible_connection':
                    self.result.connections_used.add(str(data[key]))
            
            for value in data.values():
                self._extract_features(value)
                
        elif isinstance(data, list):
            for item in data:
                self._extract_features(item)
    
    def _extract_variables(self, content: str) -> None:
        """Extract variable names from Jinja2 expressions."""
        # Simple regex to find {{ var }} patterns
        pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)'
        for match in re.finditer(pattern, content):
            self.result.vars_used.add(match.group(1))


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="sansible-compat-scan",
        description="Scan Ansible repositories for Sansible compatibility",
    )
    
    parser.add_argument(
        "repo",
        help="Path to the Ansible repository to scan",
    )
    
    parser.add_argument(
        "-o", "--output",
        dest="output_dir",
        default="./artifacts/compat_scan",
        help="Output directory for scan results (default: ./artifacts/compat_scan)",
    )
    
    parser.add_argument(
        "-f", "--format",
        dest="format",
        choices=["json", "markdown", "both"],
        default="both",
        help="Output format (default: both)",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    
    return parser


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = create_parser()
    parsed = parser.parse_args(args)
    
    # Scan the repository
    print(f"Scanning: {parsed.repo}")
    scanner = CompatibilityScanner(parsed.repo, verbose=parsed.verbose)
    result = scanner.scan()
    
    # Create output directory
    output_dir = Path(parsed.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write outputs
    if parsed.format in ("json", "both"):
        json_path = output_dir / "modules_used.json"
        json_path.write_text(json.dumps(result.to_dict(), indent=2))
        print(f"Wrote: {json_path}")
    
    if parsed.format in ("markdown", "both"):
        md_path = output_dir / "modules_used.md"
        md_path.write_text(result.to_markdown())
        print(f"Wrote: {md_path}")
    
    # Print summary
    print(f"\nSummary:")
    print(f"  Files scanned: {result.files_scanned}")
    print(f"  Playbooks found: {result.playbooks_found}")
    print(f"  Roles found: {result.roles_found}")
    print(f"  Unique modules: {len(result.modules_used)}")
    
    supported_count = sum(1 for m in result.modules_used if m in SUPPORTED_MODULES)
    total_modules = len(result.modules_used)
    
    print(f"\nCompatibility:")
    print(f"  Supported: {supported_count}/{total_modules} modules ({100*supported_count//max(1,total_modules)}%)")
    
    if result.errors:
        print(f"\nWarnings: {len(result.errors)} errors during scan")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
