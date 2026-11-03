#!/bin/bash
# Run each target in targets.txt separately and record exit code and duration.
# Usage: run_targets.sh PYTHON ANSIBLE_CORE_CHECKOUT OUT_DIR
set -u
PY=$1; SRC=$2; OUT=$3
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"; : > "$OUT/summary.tsv"
cd "$SRC"
while read -r t; do
  [ -z "$t" ] && continue
  start=$(date +%s)
  timeout 900 "$PY" bin/ansible-test integration --local --python-interpreter "$PY" "$t" > "$OUT/$t.log" 2>&1
  printf "%s\t%s\t%s\n" "$t" "$?" "$(( $(date +%s) - start ))" >> "$OUT/summary.tsv"
done < "$HERE/targets.txt"
