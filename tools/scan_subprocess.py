#!/usr/bin/env python3
"""
Subprocess/External Tool Scanner for sansible.

Scans Python source files for subprocess calls and external tool dependencies.
This helps identify what system tools the code relies on.

Usage:
    python -m tools.scan_subprocess [path]
    python -m tools.scan_subprocess --scan-upstream /upstream/ansible
"""

import argparse
import ast
import os
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional


@dataclass
class SubprocessCall:
    """A subprocess/external tool invocation."""
    file: str
    line: int
    col: int
    method: str  # subprocess.run, os.system, etc.
    command: Optional[str]  # Extracted command if static
    raw_code: str  # The actual source code


@dataclass
class ScanResult:
    """Results of scanning."""
    calls: List[SubprocessCall] = field(default_factory=list)
    files_scanned: int = 0
    errors: List[str] = field(default_factory=list)


# Methods that invoke external processes
SUBPROCESS_METHODS = {
    "subprocess.run",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "subprocess.Popen",
    "os.system",
    "os.popen",
    "os.spawn",
    "os.spawnl",
    "os.spawnle",
    "os.spawnlp",
    "os.spawnlpe",
    "os.spawnv",
    "os.spawnve",
    "os.spawnvp",
    "os.spawnvpe",
    "os.exec",
    "os.execl",
    "os.execle",
    "os.execlp",
    "os.execlpe",
    "os.execv",
    "os.execve",
    "os.execvp",
    "os.execvpe",
    "commands.getoutput",
    "commands.getstatusoutput",
}


class SubprocessScanner(ast.NodeVisitor):
    """AST visitor that finds subprocess/external tool calls."""
    
    def __init__(self, filename: str, source: str):
        self.filename = filename
        self.source_lines = source.splitlines()
        self.calls: List[SubprocessCall] = []
        self.imported_modules: Dict[str, str] = {}
    
    def visit_Import(self, node: ast.Import) -> None:
        """Track imports for alias resolution."""
        for alias in node.names:
            as_name = alias.asname or alias.name
            self.imported_modules[as_name] = alias.name
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track from imports."""
        if node.module:
            for alias in node.names:
                as_name = alias.asname or alias.name
                self.imported_modules[as_name] = f"{node.module}.{alias.name}"
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call) -> None:
        """Check for subprocess calls."""
        method_name = self._get_call_name(node)
        
        if method_name and any(method_name.endswith(m.split(".")[-1]) for m in SUBPROCESS_METHODS):
            # Try to extract the command
            command = self._extract_command(node)
            raw_code = self._get_source_line(node.lineno)
            
            self.calls.append(SubprocessCall(
                file=self.filename,
                line=node.lineno,
                col=node.col_offset,
                method=method_name,
                command=command,
                raw_code=raw_code.strip(),
            ))
        
        self.generic_visit(node)
    
    def _get_call_name(self, node: ast.Call) -> Optional[str]:
        """Get the full name of a function call."""
        if isinstance(node.func, ast.Name):
            name = node.func.id
            return self.imported_modules.get(name, name)
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                base = current.id
                base = self.imported_modules.get(base, base)
                parts.append(base)
            parts.reverse()
            return ".".join(parts)
        return None
    
    def _extract_command(self, node: ast.Call) -> Optional[str]:
        """Try to extract the command from subprocess call."""
        if not node.args:
            return None
        
        first_arg = node.args[0]
        
        # String literal
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            return first_arg.value
        
        # List of strings
        if isinstance(first_arg, ast.List):
            parts = []
            for elt in first_arg.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    parts.append(elt.value)
                else:
                    parts.append("<dynamic>")
            return " ".join(parts) if parts else None
        
        # f-string or other dynamic
        return "<dynamic>"
    
    def _get_source_line(self, lineno: int) -> str:
        """Get source code for a line."""
        if 0 < lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1]
        return ""


def scan_file(filepath: Path) -> ScanResult:
    """Scan a single Python file."""
    result = ScanResult()
    
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        
        tree = ast.parse(source, filename=str(filepath))
        scanner = SubprocessScanner(str(filepath), source)
        scanner.visit(tree)
        
        result.calls = scanner.calls
        result.files_scanned = 1
        
    except SyntaxError as e:
        result.errors.append(f"{filepath}: Syntax error: {e}")
    except Exception as e:
        result.errors.append(f"{filepath}: Error: {e}")
    
    return result


def scan_directory(dirpath: Path, exclude: Optional[Set[str]] = None) -> ScanResult:
    """Scan a directory recursively."""
    if exclude is None:
        exclude = {"__pycache__", ".git", ".tox", "venv", ".venv", "node_modules"}
    
    result = ScanResult()
    
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs if d not in exclude]
        
        for fname in files:
            if fname.endswith(".py"):
                filepath = Path(root) / fname
                file_result = scan_file(filepath)
                
                result.calls.extend(file_result.calls)
                result.files_scanned += file_result.files_scanned
                result.errors.extend(file_result.errors)
    
    return result


def extract_tool_names(result: ScanResult) -> Dict[str, int]:
    """Extract tool names from commands."""
    tools: Dict[str, int] = {}
    
    for call in result.calls:
        if call.command and call.command != "<dynamic>":
            # Get first word (the command)
            cmd = call.command.split()[0] if call.command.split() else call.command
            # Remove path
            cmd = os.path.basename(cmd)
            tools[cmd] = tools.get(cmd, 0) + 1
    
    return tools


def format_report(result: ScanResult) -> str:
    """Format scan results."""
    lines = []
    
    lines.append("=" * 60)
    lines.append("SUBPROCESS/EXTERNAL TOOL SCAN RESULTS")
    lines.append("=" * 60)
    lines.append(f"Files scanned: {result.files_scanned}")
    lines.append(f"Subprocess calls found: {len(result.calls)}")
    lines.append("")
    
    # Tool summary
    tools = extract_tool_names(result)
    if tools:
        lines.append("External tools detected:")
        lines.append("-" * 40)
        for tool, count in sorted(tools.items(), key=lambda x: -x[1]):
            lines.append(f"  {tool}: {count} usage(s)")
        lines.append("")
    
    # Group by file
    by_file: Dict[str, List[SubprocessCall]] = {}
    for call in result.calls:
        by_file.setdefault(call.file, []).append(call)
    
    lines.append("\nDetailed findings:")
    lines.append("-" * 40)
    
    for filepath in sorted(by_file.keys()):
        lines.append(f"\n{filepath}")
        for call in sorted(by_file[filepath], key=lambda x: x.line):
            lines.append(f"  Line {call.line}: {call.method}")
            if call.command:
                lines.append(f"    Command: {call.command[:60]}...")
            lines.append(f"    Code: {call.raw_code[:60]}...")
    
    return "\n".join(lines)


def format_markdown(result: ScanResult) -> str:
    """Format as Markdown."""
    lines = []
    
    lines.append("## Subprocess/External Tool Scan\n")
    lines.append(f"- Files scanned: {result.files_scanned}")
    lines.append(f"- Subprocess calls: {len(result.calls)}")
    lines.append("")
    
    # Tool table
    tools = extract_tool_names(result)
    if tools:
        lines.append("### External Tools\n")
        lines.append("| Tool | Usages | Windows Available |")
        lines.append("|------|--------|-------------------|")
        for tool, count in sorted(tools.items(), key=lambda x: -x[1]):
            # Check common Windows availability
            win_avail = "✓" if tool in {"python", "pip", "git", "ssh", "scp", "sftp"} else "?"
            lines.append(f"| `{tool}` | {count} | {win_avail} |")
    
    return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scan for subprocess calls and external tool dependencies"
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path(__file__).parent.parent / "src",
        help="Path to scan",
    )
    parser.add_argument(
        "--scan-upstream",
        type=Path,
        help="Scan upstream code",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Output as Markdown",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write to file",
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
    
    output = format_markdown(result) if args.markdown else format_report(result)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Results written to {args.output}")
    else:
        print(output)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
