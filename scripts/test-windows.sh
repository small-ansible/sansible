#!/usr/bin/env bash
# Run the test suite on a real Windows host over SSH, before pushing anything.
#
# Usage: scripts/test-windows.sh [user@host]
#   SANSIBLE_WINDOWS_HOST  ssh target (default: first argument)
#   SANSIBLE_WINDOWS_DIR   workspace on the host, forward slashes (default: <host %TEMP%>/sansible-check)
#   SANSIBLE_WINDOWS_PYTHONS  comma-separated versions (default: 3.13,3.14)
# The host needs OpenSSH server with key auth, uv, and WinRM enabled (for the PSRP test).
# Extra test targets can be passed through: SANSIBLE_TEST_SSH_*, SANSIBLE_TEST_PSRP_* (see tests/conftest.py).
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
HOST=${1:-${SANSIBLE_WINDOWS_HOST:?usage: scripts/test-windows.sh user@host}}
SSH=(ssh -o BatchMode=yes -o ConnectTimeout=15)
quiet() { grep -v -e "post-quantum" -e "pq.html" -e "vulnerable to" -e "^\*\*" || true; }

cd "$ROOT"
# private build dir: scripts/check.sh may be building into dist/ at the same time
BUILD=$(mktemp -d)
trap 'rm -rf "$BUILD"' EXIT
uv build -q --wheel -o "$BUILD"
WHEEL=$(basename "$BUILD"/sansible-*-py3-none-any.whl)

DIR=${SANSIBLE_WINDOWS_DIR:-$("${SSH[@]}" "$HOST" 'powershell -NoProfile -Command "$env:TEMP"' 2>/dev/null | tr -d '\r' | tr '\\' '/')/sansible-check}
echo "Windows host: $HOST  workspace: $DIR"

"${SSH[@]}" "$HOST" "powershell -NoProfile -Command \"New-Item -ItemType Directory -Force '$DIR' | Out-Null; Remove-Item -Recurse -Force '$DIR/tests' -ErrorAction SilentlyContinue\"" 2>&1 | quiet
tar -C "$ROOT" --exclude=__pycache__ -cf - tests | "${SSH[@]}" "$HOST" "tar -xf - -C \"$DIR\"" 2>&1 | quiet
scp -q -o BatchMode=yes "$BUILD/$WHEEL" scripts/windows/run-tests.ps1 "$HOST:$DIR/" 2>&1 | quiet

pythons=${SANSIBLE_WINDOWS_PYTHONS:-3.13,3.14}
envs=""
for var in $(compgen -e | grep -E '^SANSIBLE_TEST_(SSH|PSRP)_' || true); do
    envs+="\$env:$var='${!var}'; "
done
"${SSH[@]}" "$HOST" "powershell -NoProfile -ExecutionPolicy Bypass -Command \"${envs}& '$DIR/run-tests.ps1' -Wheel '$WHEEL' -Pythons '$pythons'\"" 2>&1 | quiet
exit "${PIPESTATUS[0]}"
