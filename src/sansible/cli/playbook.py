"""
Playbook CLI entrypoint for sansible-playbook.

Usage:
    sansible-playbook --version
    sansible-playbook --help
    sansible-playbook -i inventory playbook.yml
"""

import argparse
import sys
import platform

from sansible import __version__


def get_version_string() -> str:
    """Generate a detailed version string."""
    python_version = platform.python_version()
    os_info = f"{platform.system()} {platform.release()}"
    return (
        f"sansible-playbook {__version__}\n"
        f"  python: {python_version}\n"
        f"  platform: {os_info}\n"
        f"  pure-python: yes (no compiled extensions)"
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for sansible-playbook."""
    parser = argparse.ArgumentParser(
        prog="sansible-playbook",
        description="Run Ansible playbooks (pure-Python, Windows-native)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sansible-playbook -i inventory.ini site.yml
  sansible-playbook -i hosts playbook.yml --check
  sansible-playbook -i inventory/ deploy.yml -v
        """,
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=get_version_string(),
    )
    
    parser.add_argument(
        "playbook",
        nargs="*",
        help="Playbook file(s) to run",
    )
    
    parser.add_argument(
        "-i", "--inventory",
        dest="inventory",
        default=None,
        help="Inventory file or directory",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v, -vv, -vvv)",
    )
    
    parser.add_argument(
        "-C", "--check",
        action="store_true",
        help="Run in check mode (dry run)",
    )
    
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show differences when changing files",
    )
    
    parser.add_argument(
        "-l", "--limit",
        dest="limit",
        default=None,
        help="Limit to specific hosts/groups",
    )
    
    parser.add_argument(
        "-t", "--tags",
        dest="tags",
        default=None,
        help="Only run plays and tasks tagged with these values",
    )
    
    parser.add_argument(
        "--skip-tags",
        dest="skip_tags",
        default=None,
        help="Skip plays and tasks tagged with these values",
    )
    
    parser.add_argument(
        "-f", "--forks",
        dest="forks",
        type=int,
        default=5,
        help="Number of parallel processes (default: 5)",
    )
    
    parser.add_argument(
        "-e", "--extra-vars",
        dest="extra_vars",
        action="append",
        default=[],
        help="Extra variables as key=value or JSON (can be repeated)",
    )
    
    parser.add_argument(
        "--artifacts-dir",
        dest="artifacts_dir",
        default=None,
        help="Directory to write run artifacts (default: ./artifacts/<timestamp>)",
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )
    
    return parser


def _parse_extra_vars(extra_vars_list: list[str]) -> dict:
    """Parse extra vars from command line."""
    import json
    
    result = {}
    for item in extra_vars_list:
        item = item.strip()
        
        # Try JSON first
        if item.startswith('{'):
            try:
                result.update(json.loads(item))
                continue
            except json.JSONDecodeError:
                pass
        
        # Try key=value format
        if '=' in item:
            key, _, value = item.partition('=')
            key = key.strip()
            value = value.strip()
            
            # Try to parse value as JSON for complex types
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass  # Keep as string
            
            result[key] = value
        else:
            # Maybe it's a file path?
            from pathlib import Path
            if Path(item).exists():
                import yaml
                with open(item) as f:
                    file_vars = yaml.safe_load(f)
                    if isinstance(file_vars, dict):
                        result.update(file_vars)
    
    return result


def main(args: list[str] | None = None) -> int:
    """Main entrypoint for sansible-playbook CLI."""
    parser = create_parser()
    parsed = parser.parse_args(args)
    
    # If no playbook provided, show help
    if not parsed.playbook:
        parser.print_help()
        return 0
    
    # Validate inventory is provided
    if not parsed.inventory:
        print("ERROR: Inventory (-i/--inventory) is required", file=sys.stderr)
        return 3
    
    # Parse extra vars
    extra_vars = _parse_extra_vars(parsed.extra_vars)
    
    # Create and run the playbook runner
    from sansible.engine.runner import PlaybookRunner
    
    runner = PlaybookRunner(
        inventory_source=parsed.inventory,
        playbook_paths=parsed.playbook,
        forks=parsed.forks,
        limit=parsed.limit,
        check_mode=parsed.check,
        diff_mode=parsed.diff,
        verbosity=parsed.verbose,
        extra_vars=extra_vars,
        json_output=parsed.json,
    )
    
    return runner.run()


if __name__ == "__main__":
    sys.exit(main())
