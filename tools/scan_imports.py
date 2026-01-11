#!/usr/bin/env python3
"""
POSIX-only Import Scanner for sansible.

Scans Python source files for imports and usage patterns that are
POSIX-only and won't work on Windows.

Usage:
    python -m tools.scan_imports [path]
    python -m tools.scan_imports --scan-upstream /upstream/ansible
"""

import argparse
import ast
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional


# Modules that are POSIX-only or have limited Windows support
POSIX_ONLY_MODULES = {
    # Completely POSIX-only
    "pwd": "User password database (Unix only)",
    "grp": "Group database (Unix only)",
    "spwd": "Shadow password database (Unix only)",
    "crypt": "Unix password hashing (Unix only)",
    "posix": "POSIX system calls (Unix only)",
    "pty": "Pseudo-terminal utilities (Unix only)",
    "tty": "TTY control functions (Unix only)",
    "termios": "POSIX terminal control (Unix only)",
    "fcntl": "File control and I/O control (Unix only)",
    "pipes": "Shell pipeline template (Unix only)",
    "resource": "Resource usage limits (Unix only)",
    "syslog": "Unix syslog library (Unix only)",
    
    # Mostly POSIX (very limited on Windows)
    "curses": "Terminal handling (limited Windows support)",
    "readline": "GNU readline (limited Windows support)",
}

# Functions/attributes that are POSIX-only even in cross-platform modules
POSIX_ONLY_ATTRS = {
    "os": {
        "fork": "Process forking (Unix only)",
        "forkpty": "Fork with pseudo-terminal (Unix only)",
        "wait": "Wait for child process (Unix only)",
        "wait3": "Wait with resource info (Unix only)",
        "wait4": "Wait with resource info (Unix only)",
        "waitid": "Wait for process (Unix only)",
        "waitpid": "Wait for specific process (Unix only)",
        "getuid": "Get user ID (Unix only)",
        "geteuid": "Get effective user ID (Unix only)",
        "getgid": "Get group ID (Unix only)",
        "getegid": "Get effective group ID (Unix only)",
        "setuid": "Set user ID (Unix only)",
        "seteuid": "Set effective user ID (Unix only)",
        "setgid": "Set group ID (Unix only)",
        "setegid": "Set effective group ID (Unix only)",
        "getgroups": "Get group list (Unix only)",
        "setgroups": "Set group list (Unix only)",
        "initgroups": "Initialize groups (Unix only)",
        "getpgid": "Get process group ID (Unix only)",
        "setpgid": "Set process group ID (Unix only)",
        "getpgrp": "Get process group (Unix only)",
        "setpgrp": "Set process group (Unix only)",
        "getsid": "Get session ID (Unix only)",
        "setsid": "Set session ID (Unix only)",
        "chown": "Change file owner (Unix only)",
        "fchown": "Change file owner by fd (Unix only)",
        "lchown": "Change symlink owner (Unix only)",
        "chroot": "Change root directory (Unix only)",
        "mkfifo": "Make FIFO pipe (Unix only)",
        "mknod": "Make device node (Unix only)",
        "nice": "Change process priority (Unix only)",
        "getloadavg": "Get load average (Unix only)",
        "openpty": "Open pseudo-terminal (Unix only)",
        "fchmod": "Change mode by fd (limited Windows)",
        "lchmod": "Change symlink mode (limited Windows)",
    },
    "signal": {
        "SIGALRM": "Alarm signal (Unix only)",
        "SIGCHLD": "Child signal (Unix only)",
        "SIGCONT": "Continue signal (Unix only)",
        "SIGHUP": "Hangup signal (Unix only)",
        "SIGKILL": "Kill signal (Unix only)",
        "SIGPIPE": "Pipe signal (Unix only)",
        "SIGQUIT": "Quit signal (Unix only)",
        "SIGSTOP": "Stop signal (Unix only)",
        "SIGTSTP": "Terminal stop (Unix only)",
        "SIGTTIN": "Background read (Unix only)",
        "SIGTTOU": "Background write (Unix only)",
        "SIGUSR1": "User signal 1 (Unix only)",
        "SIGUSR2": "User signal 2 (Unix only)",
        "alarm": "Set alarm timer (Unix only)",
        "pause": "Wait for signal (Unix only)",
        "setitimer": "Set interval timer (Unix only)",
        "getitimer": "Get interval timer (Unix only)",
    },
    "socket": {
        "AF_UNIX": "Unix domain socket (Unix only)",
        "SOCK_SEQPACKET": "Sequential packet socket (Unix only)",
    },
    "subprocess": {
        "DEVNULL": "Cross-platform (ok to use)",  # Actually available on Windows
    },
}


@dataclass
class Finding:
    """A POSIX-only usage finding."""
    file: str
    line: int
    col: int
    category: str  # "import" or "attr"
    name: str
    description: str


@dataclass
class ScanResult:
    """Results of scanning a file or directory."""
    findings: List[Finding] = field(default_factory=list)
    files_scanned: int = 0
    errors: List[str] = field(default_factory=list)


class PosixScanner(ast.NodeVisitor):
    """AST visitor that finds POSIX-only imports and usages."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.findings: List[Finding] = []
        self.imported_modules: Dict[str, str] = {}  # alias -> module
    
    def visit_Import(self, node: ast.Import) -> None:
        """Handle 'import x' statements."""
        for alias in node.names:
            module_name = alias.name.split(".")[0]
            as_name = alias.asname or alias.name
            
            self.imported_modules[as_name] = module_name
            
            if module_name in POSIX_ONLY_MODULES:
                self.findings.append(Finding(
                    file=self.filename,
                    line=node.lineno,
                    col=node.col_offset,
                    category="import",
                    name=module_name,
                    description=POSIX_ONLY_MODULES[module_name],
                ))
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle 'from x import y' statements."""
        if node.module is None:
            return
        
        module_name = node.module.split(".")[0]
        
        if module_name in POSIX_ONLY_MODULES:
            self.findings.append(Finding(
                file=self.filename,
                line=node.lineno,
                col=node.col_offset,
                category="import",
                name=module_name,
                description=POSIX_ONLY_MODULES[module_name],
            ))
        
        # Track imports for attribute checking
        if module_name in POSIX_ONLY_ATTRS:
            for alias in node.names:
                name = alias.name
                if name in POSIX_ONLY_ATTRS[module_name]:
                    self.findings.append(Finding(
                        file=self.filename,
                        line=node.lineno,
                        col=node.col_offset,
                        category="attr",
                        name=f"{module_name}.{name}",
                        description=POSIX_ONLY_ATTRS[module_name][name],
                    ))
        
        self.generic_visit(node)
    
    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Handle attribute access like os.fork."""
        # Check if this is accessing a POSIX-only attribute
        if isinstance(node.value, ast.Name):
            module_alias = node.value.id
            attr = node.attr
            
            # Get the actual module name if aliased
            module_name = self.imported_modules.get(module_alias, module_alias)
            
            if module_name in POSIX_ONLY_ATTRS:
                if attr in POSIX_ONLY_ATTRS[module_name]:
                    self.findings.append(Finding(
                        file=self.filename,
                        line=node.lineno,
                        col=node.col_offset,
                        category="attr",
                        name=f"{module_name}.{attr}",
                        description=POSIX_ONLY_ATTRS[module_name][attr],
                    ))
        
        self.generic_visit(node)


def scan_file(filepath: Path) -> ScanResult:
    """Scan a single Python file for POSIX-only usage."""
    result = ScanResult()
    
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        
        tree = ast.parse(source, filename=str(filepath))
        scanner = PosixScanner(str(filepath))
        scanner.visit(tree)
        
        result.findings = scanner.findings
        result.files_scanned = 1
        
    except SyntaxError as e:
        result.errors.append(f"{filepath}: Syntax error: {e}")
    except Exception as e:
        result.errors.append(f"{filepath}: Error: {e}")
    
    return result


def scan_directory(dirpath: Path, exclude: Optional[Set[str]] = None) -> ScanResult:
    """Scan a directory recursively for POSIX-only usage."""
    if exclude is None:
        exclude = {"__pycache__", ".git", ".tox", "venv", ".venv", "node_modules"}
    
    result = ScanResult()
    
    for root, dirs, files in os.walk(dirpath):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude]
        
        for fname in files:
            if fname.endswith(".py"):
                filepath = Path(root) / fname
                file_result = scan_file(filepath)
                
                result.findings.extend(file_result.findings)
                result.files_scanned += file_result.files_scanned
                result.errors.extend(file_result.errors)
    
    return result


def format_findings(result: ScanResult) -> str:
    """Format scan results as a report."""
    lines = []
    
    # Group findings by file
    by_file: Dict[str, List[Finding]] = {}
    for f in result.findings:
        by_file.setdefault(f.file, []).append(f)
    
    # Summary
    lines.append("=" * 60)
    lines.append("POSIX-ONLY USAGE SCAN RESULTS")
    lines.append("=" * 60)
    lines.append(f"Files scanned: {result.files_scanned}")
    lines.append(f"Findings: {len(result.findings)}")
    lines.append(f"Files with findings: {len(by_file)}")
    lines.append("")
    
    # Details by file
    for filepath, findings in sorted(by_file.items()):
        lines.append(f"\n{filepath}")
        lines.append("-" * min(60, len(filepath)))
        
        for f in sorted(findings, key=lambda x: x.line):
            lines.append(f"  Line {f.line}: [{f.category}] {f.name}")
            lines.append(f"           {f.description}")
    
    # Errors
    if result.errors:
        lines.append("\n\nERRORS:")
        lines.append("-" * 40)
        for err in result.errors:
            lines.append(f"  {err}")
    
    return "\n".join(lines)


def format_inventory_md(result: ScanResult) -> str:
    """Format results as Markdown for INVENTORY.md."""
    lines = []
    
    lines.append("## POSIX-Only Usage Scan Results\n")
    lines.append(f"- Files scanned: {result.files_scanned}")
    lines.append(f"- Total findings: {len(result.findings)}")
    lines.append("")
    
    # Group by module
    by_module: Dict[str, List[Finding]] = {}
    for f in result.findings:
        module = f.name.split(".")[0]
        by_module.setdefault(module, []).append(f)
    
    lines.append("### By Module\n")
    lines.append("| Module | Usages | Files |")
    lines.append("|--------|--------|-------|")
    
    for module in sorted(by_module.keys()):
        findings = by_module[module]
        files = len(set(f.file for f in findings))
        lines.append(f"| `{module}` | {len(findings)} | {files} |")
    
    lines.append("\n### Detailed Findings\n")
    
    # Group by file
    by_file: Dict[str, List[Finding]] = {}
    for f in result.findings:
        by_file.setdefault(f.file, []).append(f)
    
    for filepath in sorted(by_file.keys()):
        lines.append(f"\n#### {filepath}\n")
        for f in sorted(by_file[filepath], key=lambda x: x.line):
            lines.append(f"- Line {f.line}: `{f.name}` - {f.description}")
    
    return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scan Python code for POSIX-only imports and usage"
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path(__file__).parent.parent / "src",
        help="Path to scan (file or directory)",
    )
    parser.add_argument(
        "--scan-upstream",
        type=Path,
        help="Scan upstream Ansible code",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Output as Markdown for INVENTORY.md",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write output to file",
    )
    
    args = parser.parse_args()
    
    path = args.scan_upstream or args.path
    
    if path.is_file():
        result = scan_file(path)
    elif path.is_dir():
        result = scan_directory(path)
    else:
        print(f"Error: Path not found: {path}")
        return 1
    
    if args.markdown:
        output = format_inventory_md(result)
    else:
        output = format_findings(result)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Results written to {args.output}")
    else:
        print(output)
    
    # Return 0 even if findings exist - this is informational
    return 0


if __name__ == "__main__":
    sys.exit(main())
