"""
Playbook CLI entrypoint for sansible-playbook.

Usage:
    sansible-playbook --version
    sansible-playbook --help
    sansible-playbook -i inventory playbook.yml

Supports most ansible-playbook options for compatibility.
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
  sansible-playbook -i hosts.yml site.yml -u admin --become
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
    
    # Inventory options
    parser.add_argument(
        "-i", "--inventory", "--inventory-file",
        dest="inventory",
        default=None,
        help="Inventory file or directory (can be comma-separated)",
    )
    
    # Verbosity
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v, -vv, -vvv, -vvvv)",
    )
    
    # Check and diff modes
    parser.add_argument(
        "-C", "--check",
        action="store_true",
        help="Run in check mode (dry run, no changes made)",
    )
    
    parser.add_argument(
        "-D", "--diff",
        action="store_true",
        help="Show differences when changing files",
    )
    
    # Host limiting
    parser.add_argument(
        "-l", "--limit",
        dest="limit",
        default=None,
        help="Limit to specific hosts/groups (pattern)",
    )
    
    # Tags
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
    
    # Parallelism
    parser.add_argument(
        "-f", "--forks",
        dest="forks",
        type=int,
        default=5,
        help="Number of parallel processes (default: 5)",
    )
    
    # Extra variables
    parser.add_argument(
        "-e", "--extra-vars",
        dest="extra_vars",
        action="append",
        default=[],
        help="Extra variables as key=value or JSON/YAML (can be repeated)",
    )
    
    # Output format
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )
    
    # Connection options
    parser.add_argument(
        "-u", "--user",
        dest="remote_user",
        default=None,
        help="Connect as this user (default: current user)",
    )
    
    parser.add_argument(
        "-c", "--connection",
        dest="connection",
        default=None,
        choices=["local", "ssh", "winrm", "paramiko"],
        help="Connection type to use (default: ssh)",
    )
    
    parser.add_argument(
        "-T", "--timeout",
        dest="timeout",
        type=int,
        default=30,
        help="Connection timeout in seconds (default: 30)",
    )
    
    parser.add_argument(
        "-k", "--ask-pass",
        dest="ask_pass",
        action="store_true",
        help="Ask for connection password",
    )
    
    parser.add_argument(
        "--private-key", "--key-file",
        dest="private_key_file",
        default=None,
        help="Use this file to authenticate the SSH connection",
    )
    
    parser.add_argument(
        "--connection-password-file", "--conn-pass-file",
        dest="connection_password_file",
        default=None,
        help="Connection password file",
    )
    
    # Privilege escalation
    parser.add_argument(
        "-b", "--become",
        dest="become",
        action="store_true",
        help="Run operations with become (privilege escalation)",
    )
    
    parser.add_argument(
        "--become-method",
        dest="become_method",
        default="sudo",
        choices=["sudo", "su", "runas"],
        help="Privilege escalation method (default: sudo)",
    )
    
    parser.add_argument(
        "--become-user",
        dest="become_user",
        default="root",
        help="Run operations as this user (default: root)",
    )
    
    parser.add_argument(
        "-K", "--ask-become-pass",
        dest="ask_become_pass",
        action="store_true",
        help="Ask for privilege escalation password",
    )
    
    parser.add_argument(
        "--become-password-file", "--become-pass-file",
        dest="become_password_file",
        default=None,
        help="File containing the become password",
    )
    
    # Vault options
    parser.add_argument(
        "--vault-password-file", "--vault-pass-file",
        dest="vault_password_file",
        default=None,
        help="Path to file containing vault password",
    )
    
    parser.add_argument(
        "--vault-id",
        dest="vault_id",
        default=None,
        help="Vault identity to use (label@source format)",
    )
    
    parser.add_argument(
        "-J", "--ask-vault-pass", "--ask-vault-password",
        dest="ask_vault_pass",
        action="store_true",
        help="Ask for vault password interactively",
    )
    
    # List/info options (no execution)
    parser.add_argument(
        "--list-hosts",
        dest="list_hosts",
        action="store_true",
        help="List matching hosts without executing tasks",
    )
    
    parser.add_argument(
        "--list-tasks",
        dest="list_tasks",
        action="store_true",
        help="List all tasks that would be executed",
    )
    
    parser.add_argument(
        "--list-tags",
        dest="list_tags",
        action="store_true",
        help="List all available tags",
    )
    
    parser.add_argument(
        "--syntax-check",
        dest="syntax_check",
        action="store_true",
        help="Perform syntax check only, do not execute",
    )
    
    # Execution control
    parser.add_argument(
        "--start-at-task",
        dest="start_at_task",
        default=None,
        help="Start playbook at the task matching this name",
    )
    
    parser.add_argument(
        "--step",
        dest="step",
        action="store_true",
        help="One-step-at-a-time: confirm each task before running",
    )
    
    parser.add_argument(
        "--force-handlers",
        dest="force_handlers",
        action="store_true",
        help="Run handlers even if a task fails",
    )
    
    parser.add_argument(
        "--flush-cache",
        dest="flush_cache",
        action="store_true",
        help="Clear the fact cache for every host",
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
    
    # Handle connection password
    connection_password = None
    if parsed.ask_pass:
        import getpass
        connection_password = getpass.getpass("SSH password: ")
    elif parsed.connection_password_file:
        from pathlib import Path
        connection_password = Path(parsed.connection_password_file).read_text().strip()
    
    # Handle become password
    become_password = None
    if parsed.ask_become_pass:
        import getpass
        become_password = getpass.getpass("BECOME password: ")
    elif parsed.become_password_file:
        from pathlib import Path
        become_password = Path(parsed.become_password_file).read_text().strip()
    
    # Handle vault password
    vault_password = None
    vault_password_file = parsed.vault_password_file
    
    if parsed.ask_vault_pass:
        import getpass
        vault_password = getpass.getpass("Vault password: ")
    
    # Handle list-only operations
    if parsed.list_hosts or parsed.list_tasks or parsed.list_tags:
        return _handle_list_operations(parsed)
    
    # Handle syntax check
    if parsed.syntax_check:
        return _handle_syntax_check(parsed)
    
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
        vault_password=vault_password,
        vault_password_file=vault_password_file,
        # New options
        remote_user=parsed.remote_user,
        connection_type=parsed.connection,
        timeout=parsed.timeout,
        private_key_file=parsed.private_key_file,
        connection_password=connection_password,
        become=parsed.become,
        become_method=parsed.become_method,
        become_user=parsed.become_user,
        become_password=become_password,
        tags=parsed.tags,
        skip_tags=parsed.skip_tags,
        start_at_task=parsed.start_at_task,
        step=parsed.step,
        force_handlers=parsed.force_handlers,
        flush_cache=parsed.flush_cache,
    )
    
    return runner.run()


def _handle_list_operations(parsed: argparse.Namespace) -> int:
    """Handle --list-hosts, --list-tasks, --list-tags operations."""
    import json
    from sansible.engine.inventory import InventoryManager
    from sansible.engine.playbook import PlaybookParser
    
    # Load inventory
    inventory = InventoryManager()
    inventory.parse(parsed.inventory)
    
    for playbook_path in parsed.playbook:
        parser = PlaybookParser(playbook_path)
        plays = parser.parse()
        
        print(f"\nplaybook: {playbook_path}")
        
        for play in plays:
            print(f"\n  play #1 ({play.name}): {play.hosts}")
            
            if parsed.list_hosts:
                hosts = inventory.get_hosts(play.hosts)
                if parsed.limit:
                    hosts = [h for h in hosts if _host_matches_limit(h, parsed.limit)]
                print("    pattern:", play.hosts)
                print("    hosts:", len(hosts))
                for host in hosts:
                    print(f"      {host.name}")
            
            if parsed.list_tasks:
                print("    tasks:")
                for i, task in enumerate(play.tasks, 1):
                    tags_str = f" TAGS: [{', '.join(task.tags)}]" if task.tags else ""
                    print(f"      {task.name}{tags_str}")
            
            if parsed.list_tags:
                all_tags = set()
                for task in play.tasks:
                    all_tags.update(task.tags)
                print("    TASK TAGS:", sorted(all_tags) if all_tags else "[]")
    
    return 0


def _handle_syntax_check(parsed: argparse.Namespace) -> int:
    """Handle --syntax-check option."""
    from sansible.engine.playbook import PlaybookParser
    
    all_ok = True
    for playbook_path in parsed.playbook:
        try:
            parser = PlaybookParser(playbook_path)
            plays = parser.parse()
            print(f"\nplaybook: {playbook_path}")
            print(f"  Syntax OK - {len(plays)} play(s)")
        except Exception as e:
            print(f"\nplaybook: {playbook_path}")
            print(f"  Syntax ERROR: {e}", file=sys.stderr)
            all_ok = False
    
    return 0 if all_ok else 4


def _host_matches_limit(host, limit: str) -> bool:
    """Check if host matches limit pattern."""
    if limit is None:
        return True
    # Simple pattern matching (Ansible supports more complex patterns)
    patterns = [p.strip() for p in limit.split(',')]
    for pattern in patterns:
        if pattern.startswith('!'):
            if host.name == pattern[1:]:
                return False
        elif pattern == host.name or pattern in host.groups:
            return True
    return limit is None


if __name__ == "__main__":
    sys.exit(main())
