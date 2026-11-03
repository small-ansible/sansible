#!/usr/bin/env bash
# Run ansible-core's own integration targets with every ansible process forced into
# Sansible's spawn worker pool, and fail if any target fails.
#
# Usage: tests/integration/run.sh ANSIBLE_CORE_CHECKOUT TARGETS_FILE OUT_DIR
#   ANSIBLE_CORE_CHECKOUT  git checkout of ansible/ansible at the pinned tag (tests live there)
#   PYTHON                 interpreter with sansible installed; must not be a venv, because some
#                          targets build nested venvs with --system-site-packages (default: python3)
set -uo pipefail

SRC=$1
TARGETS=$(realpath "$2")
mkdir -p "$3"
OUT=$(realpath "$3")
PYTHON=${PYTHON:-python3}
: > "$OUT/summary.tsv"

# ansible-test passes only a fixed set of environment variables to targets, so force the
# worker model with a .pth file instead of SANSIBLE_WORKER in the environment.
SITE=$("$PYTHON" -c "import sysconfig; print(sysconfig.get_paths()['purelib'])")
echo "import os; os.environ.setdefault('SANSIBLE_WORKER', 'pool'); os.environ.setdefault('SANSIBLE_DEBUG_LOG', '$OUT/workers.log')" \
    > "$SITE/sansible_ci_force_pool.pth"

failed=0
cd "$SRC"
while read -r target; do
    [[ -z "$target" || "$target" == \#* ]] && continue
    start=$(date +%s)
    timeout 900 "$PYTHON" bin/ansible-test integration --local --python-interpreter "$PYTHON" "$target" > "$OUT/$target.log" 2>&1
    rc=$?
    printf "%s\t%s\t%ss\n" "$target" "$rc" "$(( $(date +%s) - start ))" | tee -a "$OUT/summary.tsv"
    if [[ $rc -ne 0 ]]; then
        failed=$((failed + 1))
        echo "::group::$target failed (last 60 lines)"
        tail -60 "$OUT/$target.log"
        echo "::endgroup::"
    fi
done < "$TARGETS"

workers=$(grep -c pool-worker "$OUT/workers.log" 2>/dev/null || echo 0)
echo "spawned pool workers: $workers"
if [[ "$workers" -eq 0 ]]; then
    echo "ERROR: no pool workers were spawned; the pool was not active" >&2
    exit 1
fi
echo "$failed target(s) failed"
exit $(( failed > 0 ))
