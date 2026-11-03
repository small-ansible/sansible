#!/bin/sh
# Make every ansible process run by PYTHON load the compat layer in spawn-pool mode.
# Use a dedicated interpreter (not a venv): some targets build nested venvs with
# --system-site-packages, which only see the base interpreter's site-packages.
# Usage: install_boot.sh /path/to/dedicated/python3.13
set -eu
PYTHON=$1
HERE=$(cd "$(dirname "$0")" && pwd)
SITE=$("$PYTHON" -c "import sysconfig; print(sysconfig.get_paths()['purelib'])")
sed "s#@COMPAT_ROOT@#$(dirname "$HERE")#" "$HERE/_sansible_boot.py" > "$SITE/_sansible_boot.py"
cp "$HERE/sansible_boot.pth" "$SITE/"
"$PYTHON" -c "import sys; assert '_sansible_boot' in sys.modules; print('boot installed in', sys.prefix)"
