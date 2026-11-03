import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import compat  # noqa: F401
from ansible.cli.galaxy import main
sys.exit(main())
