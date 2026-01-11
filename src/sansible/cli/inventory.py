"""
Inventory CLI entrypoint for sansible-inventory.

Usage:
    sansible-inventory --version
    sansible-inventory --help
    sansible-inventory -i inventory --list
    sansible-inventory -i inventory --host <hostname>
"""

import argparse
import json
import sys
import platform

from sansible import __version__


def get_version_string() -> str:
    """Generate a detailed version string."""
    python_version = platform.python_version()
    os_info = f"{platform.system()} {platform.release()}"
    return (
        f"sansible-inventory {__version__}\n"
        f"  python: {python_version}\n"
        f"  platform: {os_info}\n"
        f"  pure-python: yes (no compiled extensions)"
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for sansible-inventory."""
    parser = argparse.ArgumentParser(
        prog="sansible-inventory",
        description="Show Ansible inventory information (pure-Python, Windows-native)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sansible-inventory -i inventory.ini --list
  sansible-inventory -i hosts --host webserver1
  sansible-inventory -i inventory/ --graph
        """,
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=get_version_string(),
    )
    
    parser.add_argument(
        "-i", "--inventory",
        dest="inventory",
        default=None,
        help="Inventory file or directory",
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_hosts",
        help="Output all hosts info (JSON)",
    )
    
    parser.add_argument(
        "--host",
        dest="host",
        default=None,
        help="Output specific host info (JSON)",
    )
    
    parser.add_argument(
        "--graph",
        action="store_true",
        help="Output inventory graph",
    )
    
    parser.add_argument(
        "-y", "--yaml",
        action="store_true",
        help="Output in YAML format",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity",
    )
    
    return parser


def main(args: list[str] | None = None) -> int:
    """Main entrypoint for sansible-inventory CLI."""
    parser = create_parser()
    parsed = parser.parse_args(args)
    
    # If no action specified, show help
    if not parsed.list_hosts and not parsed.host and not parsed.graph:
        parser.print_help()
        return 0
    
    # TODO: Implement inventory parsing and output
    if parsed.list_hosts:
        # Return empty inventory structure for now
        inventory = {
            "_meta": {
                "hostvars": {}
            },
            "all": {
                "children": ["ungrouped"]
            },
            "ungrouped": {
                "hosts": []
            }
        }
        print(json.dumps(inventory, indent=2))
        return 0
    
    if parsed.host:
        # Return empty hostvars for now
        hostvars: dict[str, str] = {}
        print(json.dumps(hostvars, indent=2))
        return 0
    
    if parsed.graph:
        print("@all:")
        print("  |--@ungrouped:")
        return 0
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
