#!/usr/bin/env bash
# Local gate: everything that can be verified without Windows, run before every push.
# CI should only ever confirm what this (and scripts/test-windows.sh) already proved.
#
# Usage: scripts/check.sh [--quick]     --quick skips the ansible-core integration targets
# Needs: uv, pwsh (to check the PowerShell snippets in the workflows), git.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
WORK=${SANSIBLE_CHECK_DIR:-${TMPDIR:-/tmp}/sansible-check}
QUICK=${1:-}
cd "$ROOT"
mkdir -p "$WORK"
# one run per work dir: concurrent runs reinstall packages under each other's integration targets
exec 9>"$WORK/.lock"
flock -n 9 || { echo "another scripts/check.sh is using $WORK; wait for it or set SANSIBLE_CHECK_DIR" >&2; exit 1; }
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

step "lint"
uvx ruff check src tests scripts .github/scripts

step "build"
# private build dir: scripts/test-windows.sh may be building at the same time
rm -rf "$WORK/dist"
uv build -q -o "$WORK/dist"
WHEEL=$(ls "$WORK"/dist/sansible-*-py3-none-any.whl)

step "workflow syntax and PowerShell snippets"
uv run -q --no-project --with pyyaml python scripts/check_workflows.py

step "release planning script"
python3 .github/scripts/release_plan.py plan --event push --tag "v$(sed -n 's/^__version__ = "\(.*\)"/\1/p' src/sansible/__init__.py)" > /dev/null

for py in 3.13 3.14; do
    step "tests on Python $py (installed wheel)"
    venv="$WORK/venv-$py"
    rm -rf "$venv"
    uv venv -q --python "$py" "$venv"
    VIRTUAL_ENV="$venv" uv pip install -q "$WHEEL" pytest pexpect
    "$venv/bin/sansible" doctor > "$WORK/doctor-$py.txt" || { cat "$WORK/doctor-$py.txt"; exit 1; }
    for plugin in sansible.core.paramiko sansible.core.winlocal; do
        "$venv/bin/ansible-doc" -t connection --json "$plugin" > /dev/null
    done
    (cd tests && "$venv/bin/python" -m pytest -q -p no:cacheprovider)
done

if [[ "$QUICK" != "--quick" ]]; then
    step "ansible-core integration targets under the spawn pool (quick set)"
    core=$(sed -n 's/^ANSIBLE_CORE_VERSION = "\(.*\)"/\1/p' src/sansible/__init__.py)
    src="$WORK/ansible-$core"
    [[ -d "$src" ]] || git clone -q --depth 1 --branch "v$core" https://github.com/ansible/ansible.git "$src"
    # not a venv: some targets build nested venvs with --system-site-packages
    pydir="$WORK/python-integration"
    if [[ ! -x "$pydir/python" ]]; then
        uv python install 3.13 --install-dir "$pydir/install" -q
        ln -sf "$(ls -d "$pydir"/install/cpython-3.13*/bin/python3.13 | head -1)" "$pydir/python"
    fi
    uv pip install -q --python "$pydir/python" --break-system-packages --reinstall-package sansible \
        "$WHEEL" pexpect passlib -r "$src/requirements.txt"
    PYTHON="$pydir/python" tests/integration/run.sh "$src" tests/integration/targets-quick.txt "$WORK/integration"
fi

step "all local checks passed"
