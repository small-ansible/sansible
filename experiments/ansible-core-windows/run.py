import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.environ.get("WINSIM"):
    import winsim  # noqa: F401
if os.environ.get("COMPAT"):
    import compat  # noqa: F401

if __name__ == "__main__":  # spawned workers re-import this module as __mp_main__
    from ansible.cli.playbook import main
    sys.exit(main())
