"""
Sansible CLI

Main command-line interface for running playbooks.
"""

import argparse
import sys
from pathlib import Path
from typing import List

from sansible import __version__
from sansible.engine.errors import SansibleError, ParseError, UnsupportedFeatureError
from sansible.engine.runner import PlaybookRunner


# Exit codes
EXIT_SUCCESS = 0
EXIT_HOST_FAILED = 2
EXIT_PARSE_ERROR = 3
EXIT_UNSUPPORTED = 4


def main() -> int:
    """Main entry point for the san CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.version:
        print(f"sansible {__version__}")
        return EXIT_SUCCESS
    
    if args.command == 'run':
        return run_playbook(args)
    
    parser.print_help()
    return EXIT_SUCCESS


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog='san',
        description='Small Ansible - Minimal Ansible-compatible playbook runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  san run -i inventory.ini playbook.yml
  san run -i inventory.ini playbook.yml --limit webservers
  san run -i inventory.ini playbook.yml --forks 10 --json

For more information, see: https://github.com/sansible/sansible
        """
    )
    
    parser.add_argument(
        '--version', '-V',
        action='store_true',
        help='Show version and exit'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # run command
    run_parser = subparsers.add_parser(
        'run',
        help='Run a playbook',
        description='Execute an Ansible playbook against inventory hosts'
    )
    
    run_parser.add_argument(
        'playbook',
        type=str,
        help='Path to playbook YAML file'
    )
    
    run_parser.add_argument(
        '-i', '--inventory',
        type=str,
        required=True,
        help='Path to inventory file or directory'
    )
    
    run_parser.add_argument(
        '--limit', '-l',
        type=str,
        default=None,
        help='Limit execution to specific hosts/groups'
    )
    
    run_parser.add_argument(
        '--forks', '-f',
        type=int,
        default=5,
        help='Number of parallel processes (default: 5)'
    )
    
    run_parser.add_argument(
        '--json',
        action='store_true',
        dest='json_output',
        help='Output results as JSON'
    )
    
    run_parser.add_argument(
        '--check', '-C',
        action='store_true',
        help='Run in check mode (dry run)'
    )
    
    run_parser.add_argument(
        '--diff', '-D',
        action='store_true',
        help='Show differences when changing files'
    )
    
    run_parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Increase verbosity (-v, -vv, -vvv)'
    )
    
    run_parser.add_argument(
        '-e', '--extra-vars',
        action='append',
        default=[],
        help='Extra variables (key=value or @file.yml)'
    )
    
    return parser


def run_playbook(args: argparse.Namespace) -> int:
    """Run the playbook command."""
    try:
        # Parse extra vars
        extra_vars = parse_extra_vars(args.extra_vars)
        
        # Create runner and execute
        runner = PlaybookRunner(
            inventory_source=args.inventory,
            playbook_paths=[args.playbook],
            forks=args.forks,
            limit=args.limit,
            check_mode=args.check,
            diff_mode=args.diff,
            verbosity=args.verbose,
            extra_vars=extra_vars,
            json_output=args.json_output,
        )
        
        return runner.run()
        
    except ParseError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return EXIT_PARSE_ERROR
    except UnsupportedFeatureError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return EXIT_UNSUPPORTED
    except SansibleError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        if args.verbose >= 2:
            import traceback
            traceback.print_exc()
        return 1


def parse_extra_vars(extra_vars_list: List[str]) -> dict:
    """Parse extra variables from command line."""
    import yaml
    
    result: dict = {}
    for item in extra_vars_list:
        if item.startswith('@'):
            # Load from file
            vars_file = Path(item[1:])
            if vars_file.exists():
                content = vars_file.read_text(encoding='utf-8')
                vars_data = yaml.safe_load(content) or {}
                if isinstance(vars_data, dict):
                    result.update(vars_data)
        elif '=' in item:
            # key=value format
            key, _, value = item.partition('=')
            result[key.strip()] = value.strip()
        else:
            # Try to parse as YAML/JSON
            try:
                vars_data = yaml.safe_load(item)
                if isinstance(vars_data, dict):
                    result.update(vars_data)
            except yaml.YAMLError:
                pass
    
    return result


if __name__ == '__main__':
    sys.exit(main())
