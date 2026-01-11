"""
Main CLI entrypoint for sansible.

Usage:
    sansible --version
    sansible --help
    sansible <host-pattern> -m <module> [-a <args>]
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
        f"sansible {__version__}\n"
        f"  python: {python_version}\n"
        f"  platform: {os_info}\n"
        f"  pure-python: yes (no compiled extensions)"
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for sansible."""
    parser = argparse.ArgumentParser(
        prog="sansible",
        description="Run ad-hoc Ansible commands (pure-Python, Windows-native)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sansible all -m ping
  sansible webservers -m command -a "uptime"
  sansible localhost -m setup
        """,
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=get_version_string(),
    )
    
    parser.add_argument(
        "pattern",
        nargs="?",
        default=None,
        help="Host pattern to target",
    )
    
    parser.add_argument(
        "-i", "--inventory",
        dest="inventory",
        default=None,
        help="Inventory file or directory",
    )
    
    parser.add_argument(
        "-m", "--module-name",
        dest="module",
        default="command",
        help="Module to execute (default: command)",
    )
    
    parser.add_argument(
        "-a", "--args",
        dest="module_args",
        default="",
        help="Module arguments",
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
    
    return parser


def main(args: list[str] | None = None) -> int:
    """Main entrypoint for sansible CLI."""
    parser = create_parser()
    parsed = parser.parse_args(args)
    
    # If no pattern provided, just show help
    if parsed.pattern is None:
        parser.print_help()
        return 0
    
    # TODO: Implement ad-hoc command execution
    print(f"[sansible] Target: {parsed.pattern}")
    print(f"[sansible] Module: {parsed.module}")
    print(f"[sansible] Args: {parsed.module_args}")
    print(f"[sansible] Status: Not yet implemented - M1 milestone in progress")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
